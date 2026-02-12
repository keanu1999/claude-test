"""
Performance Overview Tab — price charts, cumulative returns, period return table.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def performance_tab() -> html.Div:
    return html.Div(
        [
            # Row 1: Cumulative performance + rebased chart
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Cumulative Performance (Rebased to 100)"),
                                dbc.CardBody(dcc.Graph(id="cumulative-return-chart")),
                            ]
                        ),
                        md=8,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Period Returns (%)"),
                                dbc.CardBody(
                                    html.Div(id="period-return-table"),
                                ),
                            ]
                        ),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            # Row 2: Price chart + rolling returns
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col(html.Span("Price History"), width="auto"),
                                            dbc.Col(
                                                dbc.RadioItems(
                                                    id="price-chart-type",
                                                    options=[
                                                        {"label": "Line", "value": "line"},
                                                        {"label": "Area", "value": "area"},
                                                    ],
                                                    value="line",
                                                    inline=True,
                                                    className="ms-3",
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        align="center",
                                    ),
                                ),
                                dbc.CardBody(dcc.Graph(id="price-chart")),
                            ]
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col(html.Span("Rolling Returns"), width="auto"),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id="rolling-return-window",
                                                    options=[
                                                        {"label": "1 Month (21d)", "value": 21},
                                                        {"label": "3 Months (63d)", "value": 63},
                                                        {"label": "6 Months (126d)", "value": 126},
                                                        {"label": "1 Year (252d)", "value": 252},
                                                    ],
                                                    value=252,
                                                    clearable=False,
                                                    style={"width": "180px"},
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        align="center",
                                    ),
                                ),
                                dbc.CardBody(dcc.Graph(id="rolling-return-chart")),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            # Row 3: Drawdown chart
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Drawdown"),
                            dbc.CardBody(dcc.Graph(id="drawdown-chart")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
        ],
        className="pt-3",
    )
