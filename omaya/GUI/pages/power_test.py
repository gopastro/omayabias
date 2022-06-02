from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

# Power Test Page
layout = html.Div([
    html.H1("Power Test"),
    dbc.Button("Return to Dashboard", href="/", color="warning", className="me-md-2", style={"width": "174px"}),
], className="p-5")