from dash import Dash, html, dcc, Input, Output, callback, State
from omaya.omayadb.datamodel import OmayaLog
import dash_bootstrap_components as dbc
import datetime

# Power Test Page
layout = html.Div([
    html.H1("Power Test"),
    dbc.Button("Return to Dashboard", href="/", color="warning", className="me-md-2", style={"width": "174px"}),
    html.Hr(),
    dbc.Button("Print Logs", color="success", className="me-md-2", id="button"),
    html.Div(id="log", style={"height": "300px", "overflow": "auto", "display": "flex", "flex-direction": "column-reverse"}),
], className="p-5")

@callback(Output("log", "children"),
            State("log", "children"),
            Input("button", "n_clicks"))
def updater(arr, n_clicks):
    if arr is None:
        arr = []
    for ol in OmayaLog.select().where(OmayaLog.date>=datetime.datetime(2022, 7, 7, 13, 30, 0)).order_by(OmayaLog.date):
        arr.append(ol.date)
        arr.append(ol.logtext)
    for i in range(200):
        arr.append("Line {}\n".format(i))
    return arr