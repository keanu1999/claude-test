"""
Correlation Tab — heatmap, rolling correlation.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def correlation_tab() -> html.Div:
    return html.Div(
        [
            # Row 1: Correlation heatmap
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Return Correlation Matrix"),
                            dbc.CardBody(dcc.Graph(id="correlation-heatmap")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
            # Row 2: Rolling correlation against a reference fund
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col(html.Span("Rolling Correlation"), width="auto"),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id="correlation-ref-fund",
                                                    placeholder="Reference fund...",
                                                    style={"width": "250px"},
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id="correlation-window",
                                                    options=[
                                                        {"label": "63d", "value": 63},
                                                        {"label": "126d", "value": 126},
                                                        {"label": "252d", "value": 252},
                                                    ],
                                                    value=126,
                                                    clearable=False,
                                                    style={"width": "100px"},
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        align="center",
                                    ),
                                ),
                                dbc.CardBody(dcc.Graph(id="rolling-correlation-chart")),
                            ]
                        ),
                    ),
                ],
                className="mb-3",
            ),
        ],
        className="pt-3",
    )
