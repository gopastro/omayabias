from dash import Dash, html, dcc, Input, Output, callback
from omaya.omayadb.datamodel import OmayaLog
import dash_bootstrap_components as dbc
import datetime

# Power Test Page
layout = html.Div([
    html.H1("Power Test"),
    dbc.Button("Return to Dashboard", href="/", color="warning", className="me-md-2", style={"width": "174px"}),
    html.Hr(),
    dbc.Button("Print Logs", color="success", className="me-md-2", id="button"),
    html.Div(id="textbox"),
], className="p-5")

@callback(Output("textbox", "children"),
            Input("button", "n_clicks"))
def updater(n_clicks):
    arr = []
    for ol in OmayaLog.select().where(OmayaLog.date>=datetime.datetime(2022, 7, 7, 13, 30, 0)).order_by(OmayaLog.date):
        arr.append(ol.date)
        arr.append(ol.logtext)
    return arr