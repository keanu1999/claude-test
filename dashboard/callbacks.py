"""
Dash callbacks — wires up all interactivity between controls, data stores,
and the tab visualizations.
"""

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, html, no_update
import dash_bootstrap_components as dbc

from services.bloomberg.fund_data import FundDataProvider

# ---------------------------------------------------------------------------
# Shared Bloomberg provider (singleton per process)
# ---------------------------------------------------------------------------
_provider: FundDataProvider | None = None


def _get_provider() -> FundDataProvider:
    global _provider
    if _provider is None:
        _provider = FundDataProvider()
    return _provider


# ========================================================================= #
#  Helper: ticker display name
# ========================================================================= #

def _display_name(ticker: str) -> str:
    return FundDataProvider._clean_ticker(ticker)


# ========================================================================= #
#  Plotly template defaults
# ========================================================================= #
PLOTLY_TEMPLATE = "plotly_white"
COLOR_PALETTE = px.colors.qualitative.Set2


# ========================================================================= #
#  Callback: Add custom ticker to dropdown
# ========================================================================= #

@callback(
    Output("fund-selector", "options"),
    Output("custom-ticker-input", "value"),
    Input("add-ticker-btn", "n_clicks"),
    State("custom-ticker-input", "value"),
    State("fund-selector", "options"),
    prevent_initial_call=True,
)
def add_custom_ticker(n_clicks, ticker_input, current_options):
    if not ticker_input or not ticker_input.strip():
        return no_update, no_update
    ticker = ticker_input.strip()
    # Avoid duplicates
    existing_values = {o["value"] for o in current_options}
    if ticker not in existing_values:
        current_options.append({"label": ticker, "value": ticker})
    return current_options, ""


# ========================================================================= #
#  Callback: Load data from Bloomberg -> stores
# ========================================================================= #

@callback(
    Output("price-data-store", "data"),
    Output("fund-info-store", "data"),
    Output("risk-data-store", "data"),
    Output("loading-output", "children"),
    Output("detail-fund-selector", "options"),
    Output("correlation-ref-fund", "options"),
    Input("load-data-btn", "n_clicks"),
    State("fund-selector", "value"),
    State("date-range-picker", "start_date"),
    State("date-range-picker", "end_date"),
    State("currency-selector", "value"),
    prevent_initial_call=True,
)
def load_data(n_clicks, tickers, start_date, end_date, currency):
    if not tickers:
        return no_update, no_update, no_update, html.Span(
            "Please select at least one fund.", className="text-warning"
        ), no_update, no_update

    provider = _get_provider()
    currency = currency if currency else None

    # Default date range: 3 years
    if not start_date:
        start_date = (date.today() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    # Fetch prices
    prices = provider.get_prices(
        tickers,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
    )

    # Fetch fund info
    try:
        fund_info = provider.get_fund_info(tickers)
        fund_info_json = fund_info.to_json()
    except Exception:
        fund_info_json = "{}"

    # Compute risk metrics from prices
    risk_metrics = provider.compute_risk_metrics(prices)
    risk_json = risk_metrics.to_json()

    # Convert prices to JSON-serializable format
    price_json = prices.to_json(date_format="iso")

    # Fund options for detail / correlation selectors
    fund_opts = [{"label": _display_name(t), "value": t} for t in tickers]

    return (
        price_json,
        fund_info_json,
        risk_json,
        html.Span(
            f"Loaded data for {len(tickers)} fund(s): {start_date} to {end_date}",
            className="text-success",
        ),
        fund_opts,
        fund_opts,
    )


# ========================================================================= #
#  PERFORMANCE TAB callbacks
# ========================================================================= #

@callback(
    Output("cumulative-return-chart", "figure"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_cumulative_chart(price_json):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    cum_ret = provider.compute_cumulative_returns(prices)

    fig = go.Figure()
    for i, col in enumerate(cum_ret.columns):
        fig.add_trace(go.Scatter(
            x=cum_ret.index,
            y=cum_ret[col],
            name=_display_name(col),
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Cumulative Return (base 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


@callback(
    Output("period-return-table", "children"),
    Input("price-data-store", "data"),
    State("fund-selector", "value"),
    prevent_initial_call=True,
)
def update_period_return_table(price_json, tickers):
    if not price_json or not tickers:
        return html.P("No data loaded.")

    provider = _get_provider()
    try:
        period_ret = provider.get_period_returns(tickers)
    except Exception:
        # Fallback: compute from prices
        prices = pd.read_json(price_json)
        returns = {}
        for col in prices.columns:
            s = prices[col].dropna()
            if len(s) < 2:
                continue
            last = s.iloc[-1]
            r = {}
            for label, days in [("1D", 1), ("1W", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("YTD", None), ("1Y", 252)]:
                if label == "YTD":
                    ytd_start = s.index[s.index >= pd.Timestamp(date.today().year, 1, 1)]
                    if len(ytd_start) > 0:
                        r[label] = (last / s.loc[ytd_start[0]] - 1) * 100
                    else:
                        r[label] = np.nan
                elif days and len(s) > days:
                    r[label] = (last / s.iloc[-days - 1] - 1) * 100
                else:
                    r[label] = np.nan
            returns[_display_name(col)] = r
        period_ret = pd.DataFrame(returns)

    # Build table
    table_df = period_ret.reset_index()
    table_df.columns = ["Period"] + list(table_df.columns[1:])

    return dash_table.DataTable(
        data=table_df.round(2).to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_cell={"textAlign": "right", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_data_conditional=[
            {"if": {"filter_query": f"{{{c}}} < 0", "column_id": c}, "color": "red"}
            for c in table_df.columns[1:]
        ] + [
            {"if": {"filter_query": f"{{{c}}} > 0", "column_id": c}, "color": "green"}
            for c in table_df.columns[1:]
        ],
        style_table={"overflowX": "auto"},
    )


@callback(
    Output("price-chart", "figure"),
    Input("price-data-store", "data"),
    Input("price-chart-type", "value"),
    prevent_initial_call=True,
)
def update_price_chart(price_json, chart_type):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    fig = go.Figure()

    for i, col in enumerate(prices.columns):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        if chart_type == "area":
            fig.add_trace(go.Scatter(
                x=prices.index, y=prices[col],
                name=_display_name(col),
                fill="tozeroy",
                line=dict(color=color),
                opacity=0.6,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=prices.index, y=prices[col],
                name=_display_name(col),
                line=dict(color=color),
            ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Price",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


@callback(
    Output("rolling-return-chart", "figure"),
    Input("price-data-store", "data"),
    Input("rolling-return-window", "value"),
    prevent_initial_call=True,
)
def update_rolling_return_chart(price_json, window):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    rolling = provider.compute_rolling_returns(prices, window=window)

    fig = go.Figure()
    for i, col in enumerate(rolling.columns):
        fig.add_trace(go.Scatter(
            x=rolling.index,
            y=rolling[col] * 100,
            name=_display_name(col),
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Rolling Return (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


@callback(
    Output("drawdown-chart", "figure"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_drawdown_chart(price_json):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    dd = provider.compute_drawdown_series(prices)

    fig = go.Figure()
    for i, col in enumerate(dd.columns):
        fig.add_trace(go.Scatter(
            x=dd.index,
            y=dd[col] * 100,
            name=_display_name(col),
            fill="tozeroy",
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Drawdown (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


# ========================================================================= #
#  PEER GROUP TAB callbacks
# ========================================================================= #

@callback(
    Output("risk-return-scatter", "figure"),
    Input("risk-data-store", "data"),
    prevent_initial_call=True,
)
def update_risk_return_scatter(risk_json):
    if not risk_json:
        return go.Figure()

    risk = pd.read_json(risk_json)
    fig = go.Figure()

    for i, col in enumerate(risk.columns):
        fig.add_trace(go.Scatter(
            x=[risk.loc["Ann. Volatility", col] * 100],
            y=[risk.loc["Ann. Return", col] * 100],
            mode="markers+text",
            name=_display_name(col),
            text=[_display_name(col)],
            textposition="top center",
            marker=dict(
                size=14,
                color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
            ),
        ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        xaxis_title="Annualized Volatility (%)",
        yaxis_title="Annualized Return (%)",
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return fig


@callback(
    Output("peer-return-bar-chart", "figure"),
    Input("price-data-store", "data"),
    Input("peer-period-selector", "value"),
    prevent_initial_call=True,
)
def update_peer_return_bar(price_json, period):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    days_map = {"YTD": None, "1Y": 252, "3Y": 756, "5Y": 1260}
    days = days_map.get(period)

    returns = {}
    for col in prices.columns:
        s = prices[col].dropna()
        if len(s) < 2:
            continue
        last = s.iloc[-1]
        if period == "YTD":
            ytd_start = s.index[s.index >= pd.Timestamp(date.today().year, 1, 1)]
            if len(ytd_start) > 0:
                returns[_display_name(col)] = (last / s.loc[ytd_start[0]] - 1) * 100
        elif days and len(s) > days:
            returns[_display_name(col)] = (last / s.iloc[-days - 1] - 1) * 100

    if not returns:
        return go.Figure()

    names = list(returns.keys())
    vals = list(returns.values())
    colors = ["green" if v >= 0 else "red" for v in vals]

    fig = go.Figure(go.Bar(
        x=names,
        y=vals,
        marker_color=colors,
        text=[f"{v:.2f}%" for v in vals],
        textposition="outside",
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title=f"{period} Return (%)",
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return fig


@callback(
    Output("fund-ranking-table", "children"),
    Input("risk-data-store", "data"),
    prevent_initial_call=True,
)
def update_fund_ranking_table(risk_json):
    if not risk_json:
        return html.P("No data loaded.")

    risk = pd.read_json(risk_json)
    df = risk.T.copy()
    df.index = [_display_name(t) for t in df.index]

    # Format percentages
    for col in ["Ann. Return", "Ann. Volatility", "Max Drawdown"]:
        if col in df.columns:
            df[col] = (df[col] * 100).round(2)

    for col in ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio"]:
        if col in df.columns:
            df[col] = df[col].round(3)

    # Sort by Sharpe
    if "Sharpe Ratio" in df.columns:
        df = df.sort_values("Sharpe Ratio", ascending=False)

    df = df.reset_index().rename(columns={"index": "Fund"})

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={"textAlign": "right", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_table={"overflowX": "auto"},
        sort_action="native",
    )


@callback(
    Output("return-distribution-chart", "figure"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_return_distribution(price_json):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    returns = provider.compute_returns(prices)

    fig = go.Figure()
    for i, col in enumerate(returns.columns):
        fig.add_trace(go.Histogram(
            x=returns[col].dropna() * 100,
            name=_display_name(col),
            opacity=0.6,
            marker_color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
            nbinsx=80,
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        barmode="overlay",
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return fig


# ========================================================================= #
#  RISK ANALYSIS TAB callbacks
# ========================================================================= #

@callback(
    Output("risk-metrics-table", "children"),
    Input("risk-data-store", "data"),
    prevent_initial_call=True,
)
def update_risk_metrics_table(risk_json):
    if not risk_json:
        return html.P("No data loaded.")

    risk = pd.read_json(risk_json)
    df = risk.copy()
    df.columns = [_display_name(c) for c in df.columns]

    # Format
    for col in df.columns:
        for idx in df.index:
            val = df.loc[idx, col]
            if pd.notna(val):
                if idx in ["Ann. Return", "Ann. Volatility", "Max Drawdown"]:
                    df.loc[idx, col] = f"{val * 100:.2f}%"
                else:
                    df.loc[idx, col] = f"{val:.3f}"

    df = df.reset_index().rename(columns={"index": "Metric"})

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={"textAlign": "right", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_table={"overflowX": "auto"},
    )


@callback(
    Output("rolling-vol-chart", "figure"),
    Input("price-data-store", "data"),
    Input("vol-window-selector", "value"),
    prevent_initial_call=True,
)
def update_rolling_vol(price_json, window):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    rolling_vol = provider.compute_rolling_volatility(prices, window=window)

    fig = go.Figure()
    for i, col in enumerate(rolling_vol.columns):
        fig.add_trace(go.Scatter(
            x=rolling_vol.index,
            y=rolling_vol[col] * 100,
            name=_display_name(col),
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Annualized Volatility (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


@callback(
    Output("rolling-sharpe-chart", "figure"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_rolling_sharpe(price_json):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    rolling_sharpe = provider.compute_rolling_sharpe(prices)

    fig = go.Figure()
    for i, col in enumerate(rolling_sharpe.columns):
        fig.add_trace(go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe[col],
            name=_display_name(col),
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Sharpe Ratio",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


@callback(
    Output("var-table", "children"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_var_table(price_json):
    if not price_json:
        return html.P("No data loaded.")

    prices = pd.read_json(price_json)
    provider = _get_provider()
    returns = provider.compute_returns(prices)

    data = {}
    for col in returns.columns:
        r = returns[col].dropna()
        data[_display_name(col)] = {
            "VaR 95% (daily)": f"{r.quantile(0.05) * 100:.2f}%",
            "VaR 99% (daily)": f"{r.quantile(0.01) * 100:.2f}%",
            "CVaR 95% (daily)": f"{r[r <= r.quantile(0.05)].mean() * 100:.2f}%",
            "CVaR 99% (daily)": f"{r[r <= r.quantile(0.01)].mean() * 100:.2f}%",
        }

    df = pd.DataFrame(data).reset_index().rename(columns={"index": "Metric"})

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={"textAlign": "right", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_table={"overflowX": "auto"},
    )


@callback(
    Output("downside-stats-table", "children"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_downside_stats(price_json):
    if not price_json:
        return html.P("No data loaded.")

    prices = pd.read_json(price_json)
    provider = _get_provider()
    returns = provider.compute_returns(prices)

    data = {}
    for col in returns.columns:
        r = returns[col].dropna()
        neg = r[r < 0]
        data[_display_name(col)] = {
            "Negative Days": f"{len(neg)}",
            "Negative Days %": f"{len(neg) / len(r) * 100:.1f}%",
            "Avg Negative Return": f"{neg.mean() * 100:.3f}%",
            "Worst Day": f"{r.min() * 100:.3f}%",
            "Best Day": f"{r.max() * 100:.3f}%",
            "Skewness": f"{r.skew():.3f}",
            "Kurtosis": f"{r.kurtosis():.3f}",
        }

    df = pd.DataFrame(data).reset_index().rename(columns={"index": "Metric"})

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        style_cell={"textAlign": "right", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_table={"overflowX": "auto"},
    )


# ========================================================================= #
#  CORRELATION TAB callbacks
# ========================================================================= #

@callback(
    Output("correlation-heatmap", "figure"),
    Input("price-data-store", "data"),
    prevent_initial_call=True,
)
def update_correlation_heatmap(price_json):
    if not price_json:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    corr = provider.compute_correlation_matrix(prices)
    labels = [_display_name(c) for c in corr.columns]

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=labels,
        y=labels,
        colorscale="RdBu",
        zmid=0,
        zmin=-1,
        zmax=1,
        text=corr.round(3).values,
        texttemplate="%{text}",
        textfont={"size": 12},
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=40, r=20, t=30, b=40),
        height=500,
    )
    return fig


@callback(
    Output("rolling-correlation-chart", "figure"),
    Input("price-data-store", "data"),
    Input("correlation-ref-fund", "value"),
    Input("correlation-window", "value"),
    prevent_initial_call=True,
)
def update_rolling_correlation(price_json, ref_fund, window):
    if not price_json or not ref_fund:
        return go.Figure()

    prices = pd.read_json(price_json)
    provider = _get_provider()
    returns = provider.compute_returns(prices)

    if ref_fund not in returns.columns:
        return go.Figure()

    ref_returns = returns[ref_fund]

    fig = go.Figure()
    for i, col in enumerate(returns.columns):
        if col == ref_fund:
            continue
        rolling_corr = returns[col].rolling(window=window).corr(ref_returns)
        fig.add_trace(go.Scatter(
            x=rolling_corr.index,
            y=rolling_corr,
            name=_display_name(col),
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title=f"Correlation with {_display_name(ref_fund)}",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=30, b=40),
        hovermode="x unified",
    )
    return fig


# ========================================================================= #
#  FUND DETAILS TAB callbacks
# ========================================================================= #

@callback(
    Output("fund-info-card", "children"),
    Input("detail-fund-selector", "value"),
    Input("fund-info-store", "data"),
    prevent_initial_call=True,
)
def update_fund_info_card(ticker, fund_info_json):
    if not ticker or not fund_info_json:
        return html.P("Select a fund to see details.")

    try:
        fund_info = pd.read_json(fund_info_json)
    except Exception:
        return html.P("Could not load fund info.")

    display_ticker = _display_name(ticker)

    if display_ticker not in fund_info.columns:
        # Try original ticker
        if ticker not in fund_info.columns:
            return html.P(f"No information available for {display_ticker}.")
        col = ticker
    else:
        col = display_ticker

    info = fund_info[col].dropna()

    rows = []
    for field, value in info.items():
        rows.append(
            dbc.Row(
                [
                    dbc.Col(html.Strong(field), md=4),
                    dbc.Col(str(value), md=8),
                ],
                className="mb-1",
            )
        )

    return html.Div(rows)


@callback(
    Output("holdings-table", "children"),
    Input("detail-fund-selector", "value"),
    prevent_initial_call=True,
)
def update_holdings(ticker):
    if not ticker:
        return html.P("Select a fund.")

    provider = _get_provider()
    try:
        holdings = provider.get_fund_holdings(ticker)
        if holdings.empty:
            return html.P("No holdings data available.")
    except Exception as e:
        return html.P(f"Could not fetch holdings: {e}")

    return dash_table.DataTable(
        data=holdings.to_dict("records"),
        columns=[{"name": c, "id": c} for c in holdings.columns],
        style_cell={"textAlign": "left", "padding": "6px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_table={"overflowX": "auto"},
        page_size=20,
    )


@callback(
    Output("sector-allocation-chart", "figure"),
    Input("detail-fund-selector", "value"),
    prevent_initial_call=True,
)
def update_sector_allocation(ticker):
    if not ticker:
        return go.Figure()

    provider = _get_provider()
    try:
        sectors = provider.get_sector_allocation(ticker)
        if sectors.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)
    except Exception:
        return go.Figure().add_annotation(text="Could not load sector data", showarrow=False)

    # Assume columns like 'Sector Name' and 'Percent'
    name_col = sectors.columns[0]
    pct_col = sectors.columns[1] if len(sectors.columns) > 1 else None

    if pct_col:
        fig = go.Figure(go.Pie(
            labels=sectors[name_col],
            values=sectors[pct_col],
            textinfo="label+percent",
            hole=0.3,
        ))
    else:
        fig = go.Figure(go.Pie(
            labels=sectors[name_col],
            textinfo="label",
            hole=0.3,
        ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
    )
    return fig


@callback(
    Output("country-allocation-chart", "figure"),
    Input("detail-fund-selector", "value"),
    prevent_initial_call=True,
)
def update_country_allocation(ticker):
    if not ticker:
        return go.Figure()

    provider = _get_provider()
    try:
        countries = provider.get_country_allocation(ticker)
        if countries.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)
    except Exception:
        return go.Figure().add_annotation(text="Could not load country data", showarrow=False)

    name_col = countries.columns[0]
    pct_col = countries.columns[1] if len(countries.columns) > 1 else None

    if pct_col:
        fig = go.Figure(go.Bar(
            x=countries[name_col],
            y=countries[pct_col],
            marker_color=COLOR_PALETTE[0],
            text=[f"{v:.1f}%" for v in countries[pct_col]],
            textposition="outside",
        ))
    else:
        fig = go.Figure().add_annotation(text="No percentage data", showarrow=False)

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        yaxis_title="Allocation (%)",
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return fig
