from dash import Dash, html, dcc, Input, Output, callback, State, dash_table
#from omaya.utils.sis_test_suite import SISTestSuite
import dash_bootstrap_components as dbc
from datetime import datetime
from pandas import util

# IV Core Page
layout = html.Div([
    html.Div(id="initialization-dummy-div"),
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
                ], width=3),
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
                ], width=3)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Card Number", html_for="card-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="card-input", placeholder="Card Number", min=0, max=15)
                ], width=3)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Device Number", html_for="device-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="device-input", placeholder="Device Number", min=0, max=15)
                ], width=3)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Channel Number", html_for="channel-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="channel-input", placeholder="Channel Number", min=0, max=15)
                ], width=3)
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
                        ], value=1)
                ], width=3)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Step Count", html_for="step-input"),
                ], width=3),
                dbc.Col([
                    dbc.Input(type="number", id="step-input", placeholder="Step Count", min=0, max=5, step=0.1)
                ], width=3)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Run Test", className="me-md-2", n_clicks=0, id="submit-button"),
                ]),
            ], className="mb-3")
        ]),
        dbc.Col([
            dcc.Graph(id="graph", style={'width': '750px', 'height': '750px'})
        ])
    ]),
    html.Hr(),
    html.Div(id="output-state")
], className="p-5")

@callback(Output("directory-input", "value"),
            Input("initialization-dummy-div", "children"))
def update_output(children):
    return datetime.now().strftime("%B%d_%Y")

@callback(Output("output-state", "children"),
            Input("submit-button", "n_clicks"),
            State("directory-input", "value"),
            State("new-board-input", "value"),
            State("card-input", "value"),
            State("device-input", "value"),
            State("channel-input", "value"),
            State("temp-input", "value"),
            State("step-input", "value"))
def run_test(button_click, directory, new_board, card, device, channel, temperature, step_count):
    if(button_click>0):
        if (directory and new_board and card and device and channel and temperature and step_count) is not None:
            #sistest = SISTestSuite(directory, oldBoard=True if new_board==1 else False, card=card)
            if temperature == 1:
                vmin = -1
                vmax = 1
            else:
                vmin = -5
                vmax = 5
            #df = sistest.dc_iv_sweep(device=str(device), channel=channel, vmin=vmin, vmax=vmax, step=step_count)
            df= util.testing.makeMixedDataFrame()
            return html.Div([
                    html.H5(directory),
                    dash_table.DataTable(
                        df.to_dict("records"),
                        [{"name": i, "id": i} for i in df.columns]
                    ),
                    html.Hr()
                ])
        else:
            return "All parts of the form have not been filled up"

@callback(Output("submit-button", "color"),
            Output("submit-button", "disabled"),
            Input("directory-input", "value"),
            Input("new-board-input", "value"),
            Input("card-input", "value"),
            Input("device-input", "value"),
            Input("channel-input", "value"),
            Input("temp-input", "value"),
            Input("step-input", "value"))
def run_test(directory, new_board, card, device, channel, temperature, step_count):
    if (directory and new_board and card and device and channel and temperature and step_count) is not None:
        return "success", False
    else:
        return "danger", True