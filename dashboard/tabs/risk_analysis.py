"""
Risk Analysis Tab — volatility, drawdowns, risk metric tables, rolling risk.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def risk_analysis_tab() -> html.Div:
    return html.Div(
        [
            # Row 1: Risk metrics table
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Risk Metrics Overview"),
                            dbc.CardBody(html.Div(id="risk-metrics-table")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
            # Row 2: Rolling volatility + Rolling Sharpe
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col(html.Span("Rolling Volatility"), width="auto"),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id="vol-window-selector",
                                                    options=[
                                                        {"label": "1M (21d)", "value": 21},
                                                        {"label": "3M (63d)", "value": 63},
                                                        {"label": "6M (126d)", "value": 126},
                                                        {"label": "1Y (252d)", "value": 252},
                                                    ],
                                                    value=63,
                                                    clearable=False,
                                                    style={"width": "150px"},
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        align="center",
                                    ),
                                ),
                                dbc.CardBody(dcc.Graph(id="rolling-vol-chart")),
                            ]
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Rolling Sharpe Ratio (252d)"),
                                dbc.CardBody(dcc.Graph(id="rolling-sharpe-chart")),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            # Row 3: Worst drawdowns table + VaR
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Value at Risk (Historical, 95% & 99%)"),
                                dbc.CardBody(html.Div(id="var-table")),
                            ]
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Downside Statistics"),
                                dbc.CardBody(html.Div(id="downside-stats-table")),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
        ],
        className="pt-3",
    )
