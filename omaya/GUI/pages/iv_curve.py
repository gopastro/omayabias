from dash import Dash, html, dcc, Input, Output, callback, State, dash_table, no_update
from omaya.utils.sis_test_suite import SISTestSuite
from omaya.omayadb.datamodel import OmayaLog
import dash_bootstrap_components as dbc
from types import SimpleNamespace
from datetime import datetime
import plotly.express as px
#from pandas import util # only for testing!
import pandas as pd
import json
import threading
import time

# IV Curve Page
layout = html.Div([
    html.Div(id="initialization-dummy-div"),
    dcc.Store(id="iv-dataset"),
    dcc.Store(id="log-dataset"),
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    html.H1("IV Curve"),
                    dbc.Button("Return to Dashboard", href="/", color="warning", className="me-md-2", style={"width": "174px"}),
                    html.Hr()
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Directory", html_for="directory-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="text", id="directory-input", placeholder="Directory here")
                ], width=5),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Old/New Board", html_for="new-board-input"),
                ], width=3),
                dbc.Col([
                    dbc.RadioItems(id="new-board-input",
                        options=[
                            {"label": "New Board", "value": 1},
                            {"label": "Old Board", "value": 2},
                        ], value=1)
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Card Number", html_for="card-input"),
                ], width=3),
                dbc.Col([
                    dbc.RadioItems(
                        options=[
                            {"label": "Card 0", "value": 0},
                            {"label": "Card 1", "value": 1},
                            {"label": "Card 2", "value": 2},
                            {"label": "Card 3", "value": 3},
                        ],
                        value=0,
                        id="card-input",
                        inline=True,
                        #switch=True,
                    ),
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Device Number", html_for="device-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="text", id="device-input", placeholder="Device Number")
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Channel Number", html_for="channel-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="channel-input", placeholder="Channel Number", min=0, max=7)
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Hot/Cold Test", html_for="temp-input"),
                ], width=3),
                dbc.Col([
                    dbc.RadioItems(id="temp-input",
                        options=[
                            {"label": "Room Temperature Test", "value": 1},
                            {"label": "Cold Test", "value": 2},
                            {"label": "Dummy Load", "value": 3}
                        ], value=1)
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Vmin", html_for="vmin-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="vmin-input", placeholder="Vmin")
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Vmax", html_for="vmax-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="vmax-input", placeholder="Vmax")
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Step Count", html_for="step-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="step-input", placeholder="Step Count", value=0.1, min=0.1, max=5, step=0.1)
                ], width=4)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Run Test", className="me-md-2", n_clicks=0, id="submit-button", color="success"),
                ]),
            ], className="mb-3")
        ]),
        dbc.Col([
            html.H4("Live Logger:", style={"padding-top": "110px"}),
            html.Div(id="log", style={"height": "575px", "overflow": "auto", "display": "flex", "flex-direction": "column-reverse", "border": "dashed"})
        ])
    ]),
    html.Hr(),
    dcc.Graph(id="iv-graph", style={"margin": "auto"}),
    html.Hr(),
    html.Div(id="output-state")
], className="p-5")

@callback(Output("directory-input", "value"),
            Input("initialization-dummy-div", "children"))
def update_directory(children):
    return "DATA/"+(datetime.now().strftime("%b%d_%Y").lower())

@callback(Output("iv-dataset", "data"),
            Output("logs", "children"),
            Input("submit-button", "n_clicks"),
            State("directory-input", "value"),
            State("new-board-input", "value"),
            State("card-input", "value"),
            State("device-input", "value"),
            State("channel-input", "value"),
            State("vmin-input", "value"),
            State("vmax-input", "value"),
            State("step-input", "value"))
def run_test(button_click, directory, new_board, card, device, channel, vmin, vmax, step_count):
    def do_test():
        sistest = SISTestSuite(directory, oldBoard=False if new_board==1 else True, card=card)
        df = sistest.dc_iv_sweep(device=device, channel=channel, vmin=vmin, vmax=vmax, step=step_count, makeplot=False, calibrated=True)
        sistest.close_all()
        #df= util.testing.makeMixedDataFrame() # Only for testing!
        return df.to_json(date_format="iso", orient="split")
    logs = []
    time = datetime.now()
    
    def update_logs():
        while True:
            for ol in OmayaLog.select().where(OmayaLog.date>=time).order_by(OmayaLog.date):
                logs.append(ol.date)
                logs.append(ol.logtext)
                if ol.logtext == "Connection Closed.":
                    break
                time.sleep(0.5)
        return logs

    t1 = threading.Thread(target=do_test)
    t2 = threading.Thread(target=update_logs)

    if(button_click>0):
        if (directory is not None) and (new_board is not None) and (card is not None) and (device is not None and device != "") and (channel is not None) and (step_count is not None):
            time = datetime.now()
            dataframe = t1.start()
            logs = t2.start()
            return dataframe, logs
        else:
            return -1, logs

@callback(Output("output-state", "children"),
            Input("iv-dataset", "data"),
            prevent_initial_call=True)
def print_output(jsonified_data):
    if jsonified_data != -1 and jsonified_data is not None:
        df = pd.read_json(jsonified_data, orient="split")
        return html.Div([
                dash_table.DataTable(
                    df.to_dict("records"),
                    [{"name": i, "id": i} for i in df.columns]
                ),
                html.Hr()
            ])
    else:
        return ""

@callback(Output("iv-graph", "figure"),
            Input("iv-dataset", "data"), prevent_initial_call=True)
def make_plot(jsonified_data):
    if jsonified_data != -1 and jsonified_data is not None:
        df = pd.read_json(jsonified_data, orient="split")
        fig = px.line(x=df["Vs"], y=df["Is"], markers=True)
        fig.update_xaxes(title="Sensed Voltage [mV]", type="linear")
        fig.update_yaxes(title="Sensed Current [µA]", type="linear")
        fig.update_traces(marker=dict(size=8), mode="lines+markers")
        return fig
    else:
        return no_update

@callback(Output("submit-button", "color"),
            Output("submit-button", "disabled"),
            Input("directory-input", "value"),
            Input("new-board-input", "value"),
            Input("card-input", "value"),
            Input("device-input", "value"),
            Input("channel-input", "value"),
            Input("step-input", "value"))
def update_button(directory, new_board, card, device, channel, step_count):
    if (directory is not None) and (new_board is not None) and (card is not None) and (device is not None and device != "") and (channel is not None) and (step_count is not None):
        return "success", False
    else:
        return "danger", True

@callback(Output("vmin-input", "disabled"),
            Output("vmax-input", "disabled"),
            Output("vmin-input", "value"),
            Output("vmax-input", "value"),
            Input("temp-input", "value"))
def update_vminmax(temperature):
    if temperature == 3:
        return False, False, no_update, no_update
    elif temperature == 2:
        return True, True, -5, 5
    else:
        return True, True, -1, 1