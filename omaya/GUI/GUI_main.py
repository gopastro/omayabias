from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from pages import index, power_test, iv_core, plotter, sidebands

app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = 'OMAyA GUI'

app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/iv-core':
        return iv_core.layout
    elif pathname == '/power-test':
        return power_test.layout
    elif pathname == '/plot':
        return plotter.layout
    elif pathname == '/sidebands':
        return sidebands.layout
    else:
        return index.layout

if __name__ == '__main__':
    app.run_server(debug=False)