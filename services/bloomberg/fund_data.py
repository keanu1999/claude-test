"""
Bloomberg Fund Data Wrapper

High-level interface for fetching fund-related data from Bloomberg.
Wraps the low-level Pybbg calls into fund-specific methods with
caching and convenience transformations.
"""

from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from services.bloomberg.pybbg import Pybbg


class FundDataProvider:
    """Provides fund comparison data via Bloomberg API."""

    # Bloomberg fields for reference data
    FUND_INFO_FIELDS = [
        "FUND_ASSET_CLASS_FOCUS",
        "FUND_GEO_FOCUS",
        "FUND_STRATEGY",
        "FUND_TOTAL_ASSETS",
        "FUND_EXPENSE_RATIO",
        "FUND_INCEPT_DT",
        "FUND_MGR_STATED_FEE",
        "FUND_BENCHMARK_PRIM",
        "NAME",
        "CRNCY",
        "FUND_MGMT_CO",
    ]

    # Bloomberg fields for risk/return data
    RISK_FIELDS = [
        "VOLATILITY_260D",
        "SHARPE_RATIO_260D",
        "MAX_DRAWDOWN",
        "BETA_RAW_OVERRIDABLE",
        "ALPHA_RAW_OVERRIDABLE",
        "TRACKING_ERROR",
        "INFORMATION_RATIO",
        "SORTINO_RATIO",
    ]

    # Performance period fields
    PERFORMANCE_FIELDS = [
        "CHG_PCT_1D",
        "CHG_PCT_5D",
        "CHG_PCT_1M",
        "CHG_PCT_3M",
        "CHG_PCT_6M",
        "CHG_PCT_YTD",
        "CHG_PCT_1YR",
        "CHG_PCT_3YR",
        "CHG_PCT_5YR",
        "CHG_PCT_10YR",
    ]

    def __init__(self, host="localhost", port=8194):
        self._bbg = Pybbg(host=host, port=port)

    def stop(self):
        self._bbg.stop()

    # ------------------------------------------------------------------ #
    #  Price / Time-Series Data
    # ------------------------------------------------------------------ #

    def get_prices(
        self,
        tickers: list,
        start_date: str | date = None,
        end_date: str | date = None,
        field: str = "PX_LAST",
        periodicity: str = "DAILY",
        currency: str = None,
    ) -> pd.DataFrame:
        """
        Fetch historical prices for a list of fund tickers.

        Returns a DataFrame indexed by date with one column per ticker.
        """
        if start_date is None:
            start_date = (date.today() - timedelta(days=3 * 365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = date.today().strftime("%Y%m%d")

        df = self._bbg.bdh(
            tickers,
            field,
            start_date=start_date,
            end_date=end_date,
            periodselection=periodicity,
            fx=currency,
        )
        df.columns = [self._clean_ticker(c) for c in df.columns]
        return df

    def get_nav(self, tickers: list, start_date=None, end_date=None, currency=None) -> pd.DataFrame:
        """Fetch NAV time series (FUND_NET_ASSET_VAL)."""
        return self.get_prices(
            tickers,
            start_date=start_date,
            end_date=end_date,
            field="FUND_NET_ASSET_VAL",
            currency=currency,
        )

    def get_total_return_index(self, tickers: list, start_date=None, end_date=None, currency=None) -> pd.DataFrame:
        """Fetch total return index for accurate performance comparison."""
        return self.get_prices(
            tickers,
            start_date=start_date,
            end_date=end_date,
            field="DAY_TO_DAY_TOT_RETURN_GROSS_DVDS",
            currency=currency,
        )

    # ------------------------------------------------------------------ #
    #  Returns
    # ------------------------------------------------------------------ #

    def compute_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Compute daily simple returns from price series."""
        return prices.pct_change().dropna(how="all")

    def compute_cumulative_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Compute cumulative returns rebased to 100."""
        returns = self.compute_returns(prices)
        return (1 + returns).cumprod() * 100

    def compute_rolling_returns(self, prices: pd.DataFrame, window: int = 252) -> pd.DataFrame:
        """Compute rolling annualized returns."""
        returns = self.compute_returns(prices)
        rolling = (1 + returns).rolling(window=window).apply(
            lambda x: np.prod(x) ** (252 / window) - 1, raw=True
        )
        return rolling

    def get_period_returns(self, tickers: list) -> pd.DataFrame:
        """Fetch pre-computed period returns from Bloomberg (1D, 1M, YTD, 1Y, etc.)."""
        df = self._bbg.bdp(tickers, self.PERFORMANCE_FIELDS)
        df.index = [self._clean_ticker(t) for t in df.index]
        df.columns = [self._format_period_label(c) for c in df.columns]
        return df.T

    # ------------------------------------------------------------------ #
    #  Risk Metrics
    # ------------------------------------------------------------------ #

    def get_risk_metrics(self, tickers: list) -> pd.DataFrame:
        """Fetch risk metrics from Bloomberg for a list of funds."""
        df = self._bbg.bdp(tickers, self.RISK_FIELDS)
        df.index = [self._clean_ticker(t) for t in df.index]
        df.columns = [self._format_field_label(c) for c in df.columns]
        return df

    def compute_risk_metrics(self, prices: pd.DataFrame, rf_rate: float = 0.0) -> pd.DataFrame:
        """
        Compute risk metrics from price data.

        Returns DataFrame with: Ann. Return, Ann. Volatility, Sharpe,
        Max Drawdown, Sortino, Calmar.
        """
        returns = self.compute_returns(prices)
        metrics = {}

        for col in returns.columns:
            r = returns[col].dropna()
            ann_ret = r.mean() * 252
            ann_vol = r.std() * np.sqrt(252)
            sharpe = (ann_ret - rf_rate) / ann_vol if ann_vol > 0 else np.nan

            # Max drawdown
            cum = (1 + r).cumprod()
            running_max = cum.cummax()
            drawdown = (cum - running_max) / running_max
            max_dd = drawdown.min()

            # Sortino
            downside = r[r < 0].std() * np.sqrt(252)
            sortino = (ann_ret - rf_rate) / downside if downside > 0 else np.nan

            # Calmar
            calmar = ann_ret / abs(max_dd) if max_dd != 0 else np.nan

            metrics[col] = {
                "Ann. Return": ann_ret,
                "Ann. Volatility": ann_vol,
                "Sharpe Ratio": sharpe,
                "Max Drawdown": max_dd,
                "Sortino Ratio": sortino,
                "Calmar Ratio": calmar,
            }

        return pd.DataFrame(metrics)

    def compute_drawdown_series(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Compute drawdown time series for each fund."""
        returns = self.compute_returns(prices)
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        drawdown = (cum - running_max) / running_max
        return drawdown

    def compute_correlation_matrix(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Compute return correlation matrix between funds."""
        returns = self.compute_returns(prices)
        return returns.corr()

    def compute_rolling_volatility(self, prices: pd.DataFrame, window: int = 63) -> pd.DataFrame:
        """Compute rolling annualized volatility (default 63 days = 3 months)."""
        returns = self.compute_returns(prices)
        return returns.rolling(window=window).std() * np.sqrt(252)

    def compute_rolling_sharpe(self, prices: pd.DataFrame, window: int = 252, rf_rate: float = 0.0) -> pd.DataFrame:
        """Compute rolling Sharpe ratio."""
        returns = self.compute_returns(prices)
        rolling_ret = returns.rolling(window=window).mean() * 252
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        return (rolling_ret - rf_rate) / rolling_vol

    # ------------------------------------------------------------------ #
    #  Fund Reference / Descriptive Data
    # ------------------------------------------------------------------ #

    def get_fund_info(self, tickers: list) -> pd.DataFrame:
        """Fetch descriptive fund information from Bloomberg."""
        df = self._bbg.bdp(tickers, self.FUND_INFO_FIELDS)
        df.index = [self._clean_ticker(t) for t in df.index]
        df.columns = [self._format_field_label(c) for c in df.columns]
        return df

    def get_fund_holdings(self, ticker: str, count: int = 20) -> pd.DataFrame:
        """Fetch top fund holdings via BDS."""
        df = self._bbg.bds(ticker, "FUND_TOP_HOLDINGS")
        if len(df) > count:
            df = df.head(count)
        return df

    def get_sector_allocation(self, ticker: str) -> pd.DataFrame:
        """Fetch fund sector allocation."""
        return self._bbg.bds(ticker, "FUND_INDUSTRY_EXPOSURE")

    def get_country_allocation(self, ticker: str) -> pd.DataFrame:
        """Fetch fund country allocation."""
        return self._bbg.bds(ticker, "FUND_GEO_ALLOC")

    # ------------------------------------------------------------------ #
    #  Peer Group
    # ------------------------------------------------------------------ #

    def get_peer_group(self, ticker: str) -> pd.DataFrame:
        """Fetch peer funds from Bloomberg."""
        return self._bbg.bds(ticker, "PEER_RANKING")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clean_ticker(ticker: str) -> str:
        """Remove Bloomberg suffix for display (e.g. 'FUND GR Equity' -> 'FUND GR')."""
        parts = str(ticker).split()
        if len(parts) >= 2 and parts[-1].lower() in ("equity", "index", "comdty", "corp", "govt"):
            return " ".join(parts[:-1])
        return str(ticker)

    @staticmethod
    def _format_field_label(field: str) -> str:
        """Convert Bloomberg field name to readable label."""
        return field.replace("_", " ").title()

    @staticmethod
    def _format_period_label(field: str) -> str:
        """Convert performance field name to a short label."""
        mapping = {
            "CHG_PCT_1D": "1D",
            "CHG_PCT_5D": "1W",
            "CHG_PCT_1M": "1M",
            "CHG_PCT_3M": "3M",
            "CHG_PCT_6M": "6M",
            "CHG_PCT_YTD": "YTD",
            "CHG_PCT_1YR": "1Y",
            "CHG_PCT_3YR": "3Y",
            "CHG_PCT_5YR": "5Y",
            "CHG_PCT_10YR": "10Y",
        }
        return mapping.get(field, field)
