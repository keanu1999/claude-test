"""
Fund Comparison Dashboard — Entry point.

Usage:
    python app.py

The dashboard runs on http://localhost:8050 by default.
Requires a running Bloomberg Terminal or SAPI session on localhost:8194.
"""

import dash
import dash_bootstrap_components as dbc

from dashboard.layout import create_layout

# Import callbacks so they get registered with Dash
import dashboard.callbacks  # noqa: F401

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        dbc.icons.BOOTSTRAP,
    ],
    title="Fund Comparison Dashboard",
    suppress_callback_exceptions=True,
)

app.layout = create_layout()

server = app.server  # for gunicorn / production deployment

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
