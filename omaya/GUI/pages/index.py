from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

layout = html.Div([
    html.Div(
        dbc.Container(
            [
                html.H1("OMAyA", className="display-3"),
                html.P(
                    "Welcome to the OMAyA GUI Dashboard",
                    className="lead",
                ),
                html.Hr(className="my-2"),
                html.P(
                    "Use the following buttons to reach the specific page you need"
                ),
                html.P(
                    [dbc.Button("General Purpose Plotter", href="/plot", color="info", className="me-md-2"),
                    dbc.Button("IV Curve", href="/iv-curve", color="info", className="me-md-2"),
                    dbc.Button("Full Power Test", href="/power-test", color="info", className="me-md-2"),
                    dbc.Button("Sidebands", href="/sidebands", color="info")], className="lead"
                ),
            ],
            fluid=True,
            className="py-3",
        ),
        className="h-100 p-5 bg-light border rounded-3",
    ),
])