"""
Fund Details Tab — fund info cards, holdings, sector/country allocation.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def fund_details_tab() -> html.Div:
    return html.Div(
        [
            # Fund selector for details view
            dbc.Row(
                dbc.Col(
                    [
                        html.Label("Select Fund for Details", className="fw-bold mb-1"),
                        dcc.Dropdown(
                            id="detail-fund-selector",
                            placeholder="Select a fund...",
                        ),
                    ],
                    md=4,
                ),
                className="mb-3",
            ),
            # Row 1: Fund info card
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Fund Information"),
                            dbc.CardBody(html.Div(id="fund-info-card")),
                        ]
                    ),
                ),
                className="mb-3",
            ),
            # Row 2: Holdings + sector allocation
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Top Holdings"),
                                dbc.CardBody(html.Div(id="holdings-table")),
                            ]
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Sector Allocation"),
                                dbc.CardBody(dcc.Graph(id="sector-allocation-chart")),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            # Row 3: Country allocation
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Country / Region Allocation"),
                            dbc.CardBody(dcc.Graph(id="country-allocation-chart")),
                        ]
                    ),
                    md=6,
                ),
                className="mb-3",
            ),
        ],
        className="pt-3",
    )
