from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

layout = html.Div([
    html.Div(
        dbc.Container(
            [
                html.H1("OMAyA", className="display-3"),
                html.P(
                    "Welcome to the landing page for the OMAyA GUI",
                    className="lead",
                ),
                html.Hr(className="my-2"),
                html.P(
                    "Use the following buttons to reach the specific page you need"
                ),
                html.P(
                    [dbc.Button("IV Core", href="/iv-core", color="info", className="me-md-2"),
                    dbc.Button("Power Test", href="/power-test", color="info", className="me-md-2"),
                    dbc.Button("Plot", href="/plot", color="info", className="me-md-2"),
                    dbc.Button("Sidebands", href="/sidebands", color="info")], className="lead"
                ),
            ],
            fluid=True,
            className="py-3",
        ),
        className="h-100 p-5 bg-light border rounded-3",
    ),
])