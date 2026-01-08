import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from api_routes import api
import os
import time
import pymysql
from storm_database import StormDatabase

db_host = "mysql"
db_user = "loader"
db_pass = "loaderpass"
db_name = "storm_features"

while True:
    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
        )
        print("Connected to MySQL!")
        break
    except pymysql.MySQLError:
        print("Waiting for MySQL...")
        time.sleep(2)


# Full path to your pages folder

pages_path = os.path.join(os.path.dirname(__file__), "pages")

# Bootstrap theme + icons
external_stylesheets = [
    dbc.themes.FLATLY,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"
]

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=pages_path,
    suppress_callback_exceptions=True,
    external_stylesheets=external_stylesheets
)
server = app.server
server.register_blueprint(api)

# -------- Sidebar --------
sidebar = html.Div(
    [
        html.Div([
            html.I(className="bi bi-lightning-charge-fill me-2", style={"color": "#0a4275", "fontSize": "28px"}),
            html.H2("Storm Tracking Dashboard", style={"display": "inline", "color": "#0a4275", "fontSize": "28px"}), 
        ], style={"marginBottom": "40px"}),

        dbc.Nav(
            [
                dbc.NavLink([html.I(className="bi bi-house-door me-2"), "Home"], href="/", active="exact"),
                dbc.NavLink([html.I(className="bi bi-bar-chart-line me-2"), "Data Explorer"], href="/data-explorer", active="exact"),
                dbc.NavLink([html.I(className="bi bi-map me-2"), "Tracking Map"], href="/storm-tracking-map", active="exact"),
            ],
            vertical=True, pills=True, className="fw-semibold"
        ),

        html.Hr(),
        html.P("This dashboard allows you to explore storm analytics, patterns, and also retrieve data.",
               style={"fontSize": "13px", "color": "#555", "marginTop": "30px"}),

        html.Div("© 2025 NUS DSA3101 Storm Tracking Team 2", style={"position": "absolute", "bottom": "20px", "fontSize": "12px", "color": "#6c757d"})
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "18rem",
        "padding": "2rem 1rem",
        "background": "linear-gradient(180deg, #f8f9fa, #e3f2fd)",
        "boxShadow": "2px 0 8px rgba(0,0,0,0.1)",
    },
)

content = html.Div(
    dash.page_container,
    style={
        "marginLeft": "18rem",          # same width as sidebar
        "padding": "0",
        "backgroundColor": "#f2f3f4",
        "minHeight": "100vh",           # fill full height of screen
        "overflow": "hidden"            # no scrolling
    }
)

app.layout = html.Div([dcc.Location(id="url"), sidebar, content])

if __name__ == "__main__":
    # Preload FE DB
    stormDB = StormDatabase()
    CURRENT_EARLIEST = "01-08-2025"
    CURRENT_LATEST = "31-10-2025"
    stormDB.populateDB(CURRENT_EARLIEST, CURRENT_LATEST)

    app.run(debug=False, host="0.0.0.0", port=8050)
