from dash import Dash, html, dcc, Input, Output, callback, State, dash_table, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import datetime
import base64
import io

d_dict = dict({"Unnamed: 0": "None", "Vs":"Sensed Voltage [mV]", "Vsis":"Set Voltage [mV]", "Is": "Sensed Current [µA]",
                "T1": "Temperature 1 [K]", "T2": "Temperature 2 [K]", "T3": "Temperature 3 [K]", "T5": "Temperature 5 [K]",
                "T6": "Temperature 6 [K]", "T7": "Temperature 7 [K]", "Frequency": "IF Frequency [GHz]",
                "IFPower": "IF Power [mW]", "Power_0": "Power 0 [mW]", "Power_1": "Power 1 [mW]", "upload file": "upload file"})

# Plotter Page
layout = html.Div([
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    html.H1("General Purpose Plotter"),
                    dbc.Button("Return to Dashboard", href="/", color="warning", className="me-md-2", style={"width": "174px"}),
                    html.Hr()
                ])
            ]),
            dbc.Row([
                dcc.Upload(
                    id="upload-data",
                    children=html.Div([
                        "Drag and Drop or ",
                        html.A("Select Files")
                    ]),
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px"
                    },
                    multiple=True
                ),
                dcc.Store(id="dataset"),
                html.Div([
                    dcc.Dropdown(id="xaxis-column",placeholder="x-axis"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Linear", "value": 1},
                            {"label": "Log", "value": 2},
                        ],
                        value=1,
                        id="xaxis-type",
                    )],
                    style={"padding-bottom": "5px", "width": "90%"}),
                html.Div([
                    dcc.Dropdown(id="yaxis-column",placeholder="y-axis"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Linear", "value": 1},
                            {"label": "Log", "value": 2},
                        ],
                        value=1,
                        id="yaxis-type",
                    )],
                    style={"padding-top": "5px", "width": "90%"}
                    )
            ])
        ]),
        dbc.Col([
            dbc.Row([
                dcc.Graph(id="graph", style={'width': '750px', 'height': '750px'})
            ])
        ])
    ]),
    dbc.Row([
        html.Hr(),
        html.Div(id="output-data-upload")
    ])
], className="p-5")


def parse_contentsHTML(contents, filename, date):
    content_type, content_string = contents.split(",")
    skiprows = 0
    decoded = base64.b64decode(content_string)
    try:
        if "csv" or "txt" in filename:
            dfFirstRow = pd.read_csv(io.StringIO(decoded.decode("utf-8")), nrows=0)
            if "#" in dfFirstRow.columns[0]:
                skiprows = skiprows + 1
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), skiprows=skiprows)
        elif "xls" in filename:
            dfFirstRow = pd.read_excel(io.BytesIO(decoded), nrows=0)
            if "#" in dfFirstRow.columns[0]:
                skiprows = skiprows + 1
            df = pd.read_excel(io.BytesIO(decoded), skiprows=skiprows)
    except Exception as e:
        print(e)
        return html.Div([
            "There was an error processing this file."
        ])
    if skiprows==1:
        comments = dfFirstRow.columns
    else:
        comments = ""
    return html.Div([
        html.H5(filename),
        html.H6(comments),
        dash_table.DataTable(
            df.to_dict("records"),
            [{"name": i, "id": i} for i in df.columns]
        ),
        html.Hr()
    ])

@callback(Output("output-data-upload", "children"),
            Input("upload-data", "contents"),
            State("upload-data", "filename"),
            State("upload-data", "last_modified"))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contentsHTML(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children

def parse_contentsJSON(contents, filename, date):
    content_type, content_string = contents.split(",")
    skiprows = 0
    decoded = base64.b64decode(content_string)
    try:
        if "csv" or "txt" in filename:
            dfFirstRow = pd.read_csv(io.StringIO(decoded.decode("utf-8")), nrows=0)
            if "#" in dfFirstRow.columns[0]:
                skiprows = skiprows + 1
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), skiprows=skiprows)
        elif "xls" in filename:
            dfFirstRow = pd.read_excel(io.BytesIO(decoded), nrows=0)
            if "#" in dfFirstRow.columns[0]:
                skiprows = skiprows + 1
            df = pd.read_excel(io.BytesIO(decoded), skiprows=skiprows)
    except Exception as e:
        print(e)
    return df.to_json(date_format="iso", orient="split")

@callback(Output("dataset","data"),
            Input("upload-data","contents"),
            State("upload-data","filename"),
            State("upload-data","last_modified"))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contentsJSON(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children[0]

@callback(Output("xaxis-column","options"),
             [Input("dataset","data")])
def update_dropdown_x(jsonified_data):
    if jsonified_data is not None:
        df = pd.read_json(jsonified_data, orient="split")
        dropdown_list=[{"label": d_dict[key], "value": key} for key in df.columns]
        return dropdown_list
    return []

@callback(Output("yaxis-column","options"),
             [Input("dataset","data")])
def update_dropdown_y(jsonified_data):
    if jsonified_data is not None:
        df = pd.read_json(jsonified_data, orient="split")
        dropdown_list=[{"label": d_dict[key], "value": key} for key in df.columns]
        return dropdown_list
    return []

@callback(Output("xaxis-column","value"),
            [Input("xaxis-column","options")])
def set_xaxis_value(xaxis_options):
    if xaxis_options:
        return xaxis_options[0]["value"]

@callback(Output("yaxis-column","value"),
            [Input("yaxis-column","options")])
def set_yaxis_value(yaxis_options):
    if yaxis_options:
        return yaxis_options[0]["value"]

@callback(Output("graph", "figure"),
            [Input("dataset", "data"),
            Input("xaxis-column", "value"),
            Input("yaxis-column", "value"),
            Input("xaxis-type", "value"),
            Input("yaxis-type", "value")])
def update_graph(jsonified_data, xaxis_column_name, yaxis_column_name, xaxis_type, yaxis_type):
    if (jsonified_data and xaxis_column_name and yaxis_column_name) is not None:
        df = pd.read_json(jsonified_data, orient="split")
        fig = px.line(x=df[xaxis_column_name], y=df[yaxis_column_name], markers=True, width=750, height=750)
        fig.update_xaxes(title=xaxis_column_name, type="linear" if xaxis_type == 1 else "log")
        fig.update_yaxes(title=yaxis_column_name, type="linear" if yaxis_type == 1 else "log")
        fig.update_traces(marker=dict(size=8), mode="lines+markers")
        return fig
    else:
        return no_update