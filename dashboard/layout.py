"""
Main dashboard layout with tab navigation and fund selection controls.
"""

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.tabs.performance import performance_tab
from dashboard.tabs.peer_group import peer_group_tab
from dashboard.tabs.risk_analysis import risk_analysis_tab
from dashboard.tabs.fund_details import fund_details_tab
from dashboard.tabs.correlation import correlation_tab


# ----- Example fund universe (customize as needed) ----- #
DEFAULT_FUNDS = [
    {"label": "DWS Top Dividende (DE0009848119)", "value": "DE0009848119 GR Equity"},
    {"label": "Flossbach von Storch Multiple Opps (LU0323578657)", "value": "LU0323578657 GR Equity"},
    {"label": "Carmignac Patrimoine (FR0010135103)", "value": "FR0010135103 FP Equity"},
    {"label": "Nordea Stable Return (LU0227384020)", "value": "LU0227384020 GR Equity"},
    {"label": "BGF Global Allocation (LU0171283459)", "value": "LU0171283459 GR Equity"},
    {"label": "JPM Global Income (LU0740858492)", "value": "LU0740858492 GR Equity"},
    {"label": "Robeco QI Global Dyn Duration (LU0230242504)", "value": "LU0230242504 GR Equity"},
    {"label": "M&G Optimal Income (GB00B1VMCY93)", "value": "GB00B1VMCY93 LN Equity"},
]


def create_layout() -> html.Div:
    """Build the main dashboard layout."""
    return html.Div(
        [
            # ---- Header ---- #
            dbc.Navbar(
                dbc.Container(
                    [
                        dbc.NavbarBrand(
                            "Fund Comparison Dashboard",
                            className="fs-4 fw-bold",
                        ),
                        html.Div(
                            "Powered by Bloomberg",
                            className="text-muted small",
                        ),
                    ],
                    fluid=True,
                    className="d-flex justify-content-between align-items-center",
                ),
                color="dark",
                dark=True,
                className="mb-3",
            ),
            # ---- Controls ---- #
            dbc.Container(
                [
                    dbc.Row(
                        [
                            # Fund selector
                            dbc.Col(
                                [
                                    html.Label("Select Funds", className="fw-bold mb-1"),
                                    dcc.Dropdown(
                                        id="fund-selector",
                                        options=DEFAULT_FUNDS,
                                        value=[DEFAULT_FUNDS[0]["value"], DEFAULT_FUNDS[1]["value"]],
                                        multi=True,
                                        placeholder="Enter Bloomberg tickers or select funds...",
                                        style={"minWidth": "400px"},
                                    ),
                                ],
                                md=5,
                            ),
                            # Custom ticker input
                            dbc.Col(
                                [
                                    html.Label("Add Custom Ticker", className="fw-bold mb-1"),
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="custom-ticker-input",
                                                placeholder="e.g. LU0123456789 GR Equity",
                                                type="text",
                                            ),
                                            dbc.Button(
                                                "Add",
                                                id="add-ticker-btn",
                                                color="primary",
                                                n_clicks=0,
                                            ),
                                        ],
                                    ),
                                ],
                                md=3,
                            ),
                            # Date range
                            dbc.Col(
                                [
                                    html.Label("Date Range", className="fw-bold mb-1"),
                                    dcc.DatePickerRange(
                                        id="date-range-picker",
                                        display_format="DD.MM.YYYY",
                                        start_date_placeholder_text="Start",
                                        end_date_placeholder_text="End",
                                        className="w-100",
                                    ),
                                ],
                                md=2,
                            ),
                            # Currency
                            dbc.Col(
                                [
                                    html.Label("Currency", className="fw-bold mb-1"),
                                    dcc.Dropdown(
                                        id="currency-selector",
                                        options=[
                                            {"label": "Local", "value": ""},
                                            {"label": "EUR", "value": "EUR"},
                                            {"label": "USD", "value": "USD"},
                                            {"label": "GBP", "value": "GBP"},
                                            {"label": "CHF", "value": "CHF"},
                                        ],
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                md=2,
                            ),
                        ],
                        className="mb-3 g-3",
                    ),
                    # ---- Load button ---- #
                    dbc.Row(
                        dbc.Col(
                            dbc.Button(
                                [html.I(className="bi bi-download me-2"), "Load Data"],
                                id="load-data-btn",
                                color="success",
                                size="lg",
                                n_clicks=0,
                                className="mb-3",
                            ),
                            width="auto",
                        ),
                    ),
                    # ---- Loading spinner ---- #
                    dcc.Loading(
                        id="loading-indicator",
                        type="circle",
                        children=html.Div(id="loading-output"),
                    ),
                    # ---- Shared data store ---- #
                    dcc.Store(id="price-data-store"),
                    dcc.Store(id="fund-info-store"),
                    dcc.Store(id="risk-data-store"),
                    # ---- Tabs ---- #
                    dbc.Tabs(
                        [
                            dbc.Tab(performance_tab(), label="Performance Overview", tab_id="tab-performance"),
                            dbc.Tab(peer_group_tab(), label="Peer Group Analysis", tab_id="tab-peer"),
                            dbc.Tab(risk_analysis_tab(), label="Risk Analysis", tab_id="tab-risk"),
                            dbc.Tab(correlation_tab(), label="Correlation", tab_id="tab-correlation"),
                            dbc.Tab(fund_details_tab(), label="Fund Details", tab_id="tab-details"),
                        ],
                        id="dashboard-tabs",
                        active_tab="tab-performance",
                        className="mb-3",
                    ),
                ],
                fluid=True,
            ),
            # ---- Footer ---- #
            html.Footer(
                dbc.Container(
                    html.P(
                        "Fund Comparison Dashboard — Data sourced from Bloomberg",
                        className="text-center text-muted py-3 mb-0",
                    ),
                    fluid=True,
                ),
                className="bg-light mt-4",
            ),
        ]
    )
