"""
Peer Group Analysis Tab — scatter plots, ranking tables, distribution charts.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def peer_group_tab() -> html.Div:
    return html.Div(
        [
            # Row 1: Risk-Return scatter + period return bar chart
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Risk / Return Scatter"),
                                dbc.CardBody(dcc.Graph(id="risk-return-scatter")),
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
                                            dbc.Col(html.Span("Return Comparison"), width="auto"),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id="peer-period-selector",
                                                    options=[
                                                        {"label": "YTD", "value": "YTD"},
                                                        {"label": "1Y", "value": "1Y"},
                                                        {"label": "3Y", "value": "3Y"},
                                                        {"label": "5Y", "value": "5Y"},
                                                    ],
                                                    value="1Y",
                                                    clearable=False,
                                                    style={"width": "120px"},
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        align="center",
                                    ),
                                ),
                                dbc.CardBody(dcc.Graph(id="peer-return-bar-chart")),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            # Row 2: Rankings table
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Fund Rankings (Sorted by Sharpe Ratio)"),
                            dbc.CardBody(html.Div(id="fund-ranking-table")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
            # Row 3: Return distribution
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Daily Return Distribution"),
                            dbc.CardBody(dcc.Graph(id="return-distribution-chart")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
        ],
        className="pt-3",
    )
