from dash import Dash, html, dcc, Input, Output, callback, State, dash_table, no_update, ALL, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
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
                    html.H1("General Purpose Plotter", id="initializer"),
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
                dcc.Store(id="filecount"),
                html.Div(id="axis-options-container",
                    style={"padding-top": "5px", "width": "90%"})
            ])
        ]),
        dbc.Col([
            dbc.Row([
                dcc.Graph(id="graph", style={'width': '1000px', 'height': '750px'})
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
        return children


@callback(Output("axis-options-container", "children"),
            Output("filecount", "data"),
            Input("dataset", "data"))
def add_axis_options(data):
    if data is not None:
        div = []
        for i in range(len(data)):
            div.append(html.H3("Graph {}".format(i)))
            div.append(html.Div([
                    dcc.Dropdown(id={'type': 'xaxis-column', 'index': i}, placeholder="x-axis"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Linear", "value": 1},
                            {"label": "Log", "value": 2},
                        ],
                        value=1,
                        id={'type': 'xaxis-type', 'index': i},
                    )]))
            div.append(html.Div([
                    dcc.Dropdown(id={'type': 'yaxis-column', 'index': i}, placeholder="y-axis"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Linear", "value": 1},
                            {"label": "Log", "value": 2},
                        ],
                        value=1,
                        id={'type': 'yaxis-type', 'index': i},
                    )]))
        return div, len(data)
    else:
        return no_update, 0


@callback(Output({'type': 'xaxis-column', 'index': ALL}, "options"),
            Output({'type': 'xaxis-column', 'index': ALL},"value"),
            Output({'type': 'yaxis-column', 'index': ALL},"options"),
            Output({'type': 'yaxis-column', 'index': ALL},"value"),
            State("dataset","data"),
            Input("filecount", "data"))
def update_dropdown_x(jsonified_data, number):
    if jsonified_data is not None:
        lists = []
        value = []
        for i in range(number):
            df = pd.read_json(jsonified_data[i], orient="split")
            dropdown_list=[{"label": d_dict[key], "value": key} for key in df.columns]
            lists.append(dropdown_list)
            value.append(dropdown_list[0]["value"])
        return lists, value, lists, value
    return [], no_update, [], no_update

@callback(Output({'type': 'xaxis-type', 'index': ALL}, "value"),
            Input({'type': 'xaxis-type', 'index': ALL},"value"), prevent_initial_call=True)
def radio_update(value):
    button_value = callback_context.triggered[0]["value"] if not None else -1
    if button_value is not -1:
        return list(map(lambda x: button_value, value))
    else:
        return no_update

@callback(Output("graph", "figure"),
            Input("dataset", "data"),
            Input({'type': 'xaxis-column', 'index': ALL}, "value"),
            Input({'type': 'yaxis-column', 'index': ALL}, "value"),
            Input({'type': 'xaxis-type', 'index': ALL}, "value"),
            Input({'type': 'yaxis-type', 'index': ALL}, "value"))
def update_graph(jsonified_data, xaxis_column_names, yaxis_column_names, xaxis_types, yaxis_types):
    if (jsonified_data is not None) and len(xaxis_column_names)>0 and len(yaxis_column_names)>0:
        layout = {"width":1000, "height":750}
        traces = []
        yaxis_bool = True
        for i in range(len(jsonified_data)):
            df = pd.read_json(jsonified_data[i], orient="split")
            traces.append({'x': df[xaxis_column_names[i]], 'y': df[yaxis_column_names[i]], 'name': d_dict[yaxis_column_names[i]], 'yaxis': f"y{'' if i==0 else i+1}"})
            if i==0:
                layout[f"yaxis{i+1}"] = {'title': d_dict[yaxis_column_names[i]], 'titlefont': {'color': 'black'}, 'tickfont': {'color': 'black'}, "type":"linear" if yaxis_types[i] == 1 else "log"}
            else:
                if yaxis_bool:
                    layout[f"yaxis{i+1}"] = {'title': d_dict[yaxis_column_names[i]], 'side': 'left', 'overlaying': 'y', 'anchor': 'free', 'titlefont': {'color': 'black'}, 'tickfont': {'color': 'black'}, "type":"linear" if yaxis_types[i] == 1 else "log"}
                else:
                    layout[f"yaxis{i+1}"] = {'title': d_dict[yaxis_column_names[i]], 'side': 'right', 'overlaying': 'y', 'anchor': 'x', 'titlefont': {'color': 'black'}, 'tickfont': {'color': 'black'}, "type":"linear" if yaxis_types[i] == 1 else "log"}
            yaxis_bool = not yaxis_bool
        layout['xaxis'] = {'domain': [0.05, 0.95], "type":"linear" if xaxis_types[0] == 1 else "log"}
        fig = pio.from_json(pio.to_json({'data': traces, 'layout': layout}))
        return fig
    else:
        return no_update