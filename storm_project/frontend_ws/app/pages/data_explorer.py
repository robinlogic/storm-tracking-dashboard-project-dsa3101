import os
import pandas as pd
from dash import html, dcc, register_page, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash_ag_grid import AgGrid
import numpy as np
import sys
import dash
import time
sys.path.append(os.path.dirname(__file__) + "/..")
from storm_database import StormDatabase


register_page(__name__, path="/data-explorer")

# ----------------------------------------------------------
# 1. DB setup
# ----------------------------------------------------------
#DB_URL = "mysql+pymysql://root:dsa3101@127.0.0.1:5002/storm_features"

def get_db(start=None, end=None):
    """Always query via StormDatabase abstraction."""
    db = StormDatabase()
    return db

storm_db = StormDatabase()
df_init = storm_db.get_storm_profiles("2025-07-01", "2025-10-31")
min_date, max_date = df_init["datetime"].min(), df_init["datetime"].max()

min_date = min_date.normalize()  # 2025-08-01 00:00:00
max_date = (max_date + pd.Timedelta(days=1)).normalize()

df_rainy = storm_db.get_rainy_days(min_date, max_date).copy()
df_rainy["date"] = pd.to_datetime(df_rainy["date"])

# Even if earliest record isn't the 1st, we anchor it to that month
min_month = pd.Timestamp(df_rainy["date"].min().year, df_rainy["date"].min().month, 1)
max_month = (df_rainy["date"].max() + pd.offsets.MonthEnd(0)).normalize()

# ----------------------------------------------------------
# 2. Layout
# ----------------------------------------------------------
layout = dbc.Container([
    # Hidden dropdown (used only for internal callbacks)
    dcc.Dropdown(
        id="storm-param-dropdown",
        options=[
            {"label": "Storm Area", "value": "storm_area_km2"},
            {"label": "Storm Distance", "value": "storm_distance_km"},
            {"label": "Storm Duration", "value": "storm_duration_min"},
            {"label": "Rainy Days", "value": "rainy_days"},
        ],
        value=None,
        style={"display": "none"}  # completely hidden from user
    ),
    dcc.Store(id="raw-data-store", storage_type="memory"),  # could be 'session' too

    
    html.Div([
        # --- Top-right corner API button ---
        html.Div([
            dbc.Button(
                "API Access",
                id="open-api-modal",
                color="info",
                outline=True,
                className="position-absolute top-0 end-0 m-3",
                style={
                    "fontWeight": "600",
                    "borderRadius": "8px",
                    "padding": "8px 16px",
                    "zIndex": 10
                }
            ),
            dbc.Modal([
                dbc.ModalHeader("Sample OpenAPI Query"),
                dbc.ModalBody(id="api-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-api-modal", color="primary", className="ms-auto")
                )
            ], id="api-modal", is_open=False, size="lg", scrollable=True, backdrop="static")
        ]),
    
        # --- Title + Subtitle ---
        html.Div([
            html.H1(
                "Data Explorer",
                style={
                    "color": "#0a4275",
                    "fontWeight": "800",
                    "marginBottom": "0.4rem",
                    "fontSize": "2.6rem",
                    "textAlign": "center"
                }
            ),
            html.P(
                "Explore storm metrics and rainfall summaries interactively.",
                style={
                    "fontSize": "1.1rem",
                    "color": "#555",
                    "textAlign": "center",
                    "marginBottom": "0"
                }
            )
        ], style={
            "position": "relative",
            "paddingTop": "0.5rem"
        }),
    ], style={
        "position": "relative",
        "marginBottom": "2rem"
    }),

    dcc.Store(id="page-loaded", data=True),
    dcc.Store(id="init-trigger", data=True),
    
    # --- Filters ---
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("Select Parameter", className="fw-bold text-center mb-3", style={"color": "#0a4275"}),
    
                # Parameter cards (4 selectable buttons)
                dbc.Row([
                    dbc.Col(dbc.Button("Storm Area", id="param-storm_area_km2", outline=True, color="primary", n_clicks=0, className="w-100 param-btn"), width=3),
                    dbc.Col(dbc.Button("Storm Distance", id="param-storm_distance_km", outline=True, color="primary", n_clicks=0, className="w-100 param-btn"), width=3),
                    dbc.Col(dbc.Button("Storm Duration", id="param-storm_duration_min", outline=True, color="primary", n_clicks=0, className="w-100 param-btn"), width=3),
                    dbc.Col(dbc.Button("Rainy Days", id="param-rainy_days", outline=True, color="primary", n_clicks=0, className="w-100 param-btn"), width=3),
                ], justify="center", className="g-2 mb-4"),
    
                # Date range slider
                html.Div([
                    html.Label(
                        "Select Date Range",
                        className="fw-semibold mb-2 text-center",
                        style={"display": "block", "fontSize": "20px", "color": "#0a4275"}
                    ),
                    dcc.RangeSlider(
                        id="date-slider",
                        min=0,
                        max=(pd.to_datetime(max_date) - pd.to_datetime(min_date)).days,
                        value= [0, (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days],
                        step=1,
                        allowCross=False,
                        marks={
                            0: {"label": "Start", "style": {"color": "#0a4275", "fontWeight": "600"}},
                            (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days: {
                                "label": "End", "style": {"color": "#0a4275", "fontWeight": "600"}}
                        },
                        tooltip={"always_visible": False, "placement": "bottom"},
                    ),
                    html.Div(id="slider-date-display", className="text-center mt-2 fw-bold", style={"color": "#0a4275"})
                ], style={"width": "90%", "margin": "0 auto", "textAlign": "center"})
            ])
        ], width=12)
    ], className="justify-content-center mb-4"),
    
    html.Hr(),

    # --- Table + Plots ---
    # Plots side-by-side above the table
    dbc.Row([
        dbc.Col([
            html.H4([
                "Raw Data Trend ",
                html.I(className="bi bi-info-circle ms-2", id="info-raw-trend", style={"cursor": "pointer", "color": "#0a4275"}),
            dbc.Button("Download Raw Data CSV", id="download-raw-btn", size="sm", color="primary", outline=True, className="ms-3", n_clicks=0),
                dcc.Download(id="download-raw")
            ], className="text-secondary text-center mb-2"),
            dcc.Graph(id="raw-storm-plot", style={"height": "380px"})
        ], width=6),
        
        dbc.Col([
            html.H4([
                "Cleaned Data Trend ",
                html.I(className="bi bi-info-circle ms-2", id="info-clean-trend", style={"cursor": "pointer", "color": "#0a4275"}),
            dbc.Button("Download Cleaned Data CSV", id="download-clean-btn", size="sm", color="primary", outline=True, className="ms-3", n_clicks=0),
                dcc.Download(id="download-clean")
            ], className="text-secondary text-center mb-2"),
            dcc.Graph(id="cleaned-storm-plot", style={"height": "380px"})
        ], width=6)
    ], className="g-4 mb-2"),

    # --- Hover Tooltips for Raw & Cleaned Data Trend ---
    dbc.Tooltip(
        "Raw Data Trend includes all storms, including those flagged as outliers by Mahalanobis Distance. "
        "It provides a complete view of storm behaviour, though some points may be extreme. "
        "The formula for the best-fit line is indicated in the subtitle.",
        target="info-raw-trend",
        placement="top",
        style={"fontSize": "14px", "maxWidth": "350px"}
    ),
    
    dbc.Tooltip(
        "Cleaned Data Trend removes storms detected as outliers, allowing clearer interpretation of general storm trends "
        "without the influence of anomalous events. "
        "The formula for the best-fit line (which does not include outlier storms) is indicated in the subtitle.",
        target="info-clean-trend",
        placement="top",
        style={"fontSize": "14px", "maxWidth": "350px"}
    ),

    html.Div([  
        html.Div([
            html.H4([
                "Raw Data (with Outliers indicated) ",
                html.I(className="bi bi-info-circle ms-2", id="info-icon", style={"cursor": "pointer", "color": "#0a4275"}),
            ], className="text-secondary mb-0", style={"display": "inline-block"}),
        
            dbc.Button(
                "Show Legend", id="toggle-legend-btn", outline=True, color="primary",
                size="sm", className="ms-3", n_clicks=0
            )
        ], className="text-center mb-2"),

        # Table Column Legend
        html.Div(
            id="legend-container",
            children=[
                html.Div([
                    html.H5("Legend:", style={
                        "textAlign": "left",
                        "fontWeight": "bold",
                        "marginBottom": "4px",
                        "marginTop": "10px"
                    }),
                    html.Ul([
                        html.Li("Storm_id: Unique identifier of a storm."),
                        html.Li("Date/Datetime: The date and timestamp when the data was captured."),
                        html.Li("Storm_area_km2: Instantaneous area of the storm at the corresponding timestamp."),
                        html.Li("Storm_centroid_lat: Instantaneous latitude of the storm centroid."),
                        html.Li("Storm_centroid_long: Instantaneous longitude of the storm centroid."),
                        html.Li("Number_of_rainy_days: The total number of days with storms for the corresponding month."),
                        html.Li("Outlier: Identifies if the storm_id was classified as an outlier according to our modelling."),
                    ], style={
                        "fontSize": "15px",
                        "textAlign": "left",
                        "color": "#444",
                        "marginLeft": "20px"
                    })
                ])
            ],
            style={"marginBottom": "10px"}
        ),
        
        dbc.Modal([
            dbc.ModalHeader("About Outlier Detection (Mahalanobis Distance)"),
            dbc.ModalBody([
                html.P("""
                The Mahalanobis Distance is a multivariate outlier detection technique used to 
                identify unusual storms based on how far they deviate from the overall data distribution.
                Unlike simple distance measures such as Euclidean distance, Mahalanobis distance accounts for 
                correlations between variables, making it ideal for datasets where storm attributes 
                (like area, duration, distance, and rainfall) are interdependent.
                """),
            
                html.P("""
                The implemented method first computes each storm’s distance from the mean storm profile 
                using the covariance matrix of the dataset. These distances are then compared against a 
                Chi-Square statistical threshold to flag storms that are significantly different from 
                the majority. In this project, storms with unusually large Mahalanobis distances are 
                classified as outliers, labelled as "TRUE" under the "outlier" column of the table, and excluded 
                from the cleaned plots and aggregates.
                """),
            
                html.P([
                    "You can learn more about the Mahalanobis Distance and how it works ",
                    html.A("in this Medium article.", 
                           href="https://dilipkumar.medium.com/mahalanobis-distance-usage-in-machine-learning-2bd4bcacbcd2",
                           target="_blank", style={"color": "#0a4275", "textDecoration": "underline"})
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id="close-info", color="primary", className="ms-auto")
            ),
        ], id="info-modal", is_open=False),

        # Table occupies full width, bottom half of screen
        dcc.Store(id="raw-data-store", storage_type="session"),
        html.Div([
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        "← Previous",
                        id="prev-page",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                        className="me-2",
                        style={
                            "fontWeight": "600",
                            "borderRadius": "8px",
                            "padding": "6px 18px",
                            "fontSize": "15px",
                            "backgroundColor": "white",
                            "borderColor": "#0a4275",
                            "color": "#0a4275",
                            "transition": "all 0.2s ease-in-out"
                        }
                    ),
                    width="auto"
                ),
                dbc.Col(
                    dcc.Input(
                        id="page-input",
                        type="number",
                        min=1,
                        value=1,
                        style={"width": "70px", "textAlign": "center"}
                    ),
                    width="auto",
                    className="text-center align-self-center"
                ),
                dbc.Col(
                    html.Span(id="page-info", 
                              style={ "fontWeight": "600", 
                                      "color": "#0a4275", 
                                      "fontSize": "16px", 
                                      "verticalAlign": "middle", 
                                      "margin": "0 10px" } ), 
                    width="auto", className="text-center align-self-center" 
                ),

                dbc.Col(
                    dbc.Button(
                        "Next →",
                        id="next-page",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                        className="ms-2",
                        style={
                            "fontWeight": "600",
                            "borderRadius": "8px",
                            "padding": "6px 18px",
                            "fontSize": "15px",
                            "backgroundColor": "white",
                            "borderColor": "#0a4275",
                            "color": "#0a4275",
                            "transition": "all 0.2s ease-in-out"
                        }
                    ),
                    width="auto"
                ),
            ], justify="center", align="center", className="my-3 g-0"),
        ]),
        html.Div(id="table-container"),
      ], style={"paddingBottom": "50px"})  
    ]),

# ----------------------------------------------------------
# 3. Dynamically adjust slider granularity (Days vs Months)
# ----------------------------------------------------------
@callback(
    Output("date-slider", "min"),
    Output("date-slider", "max"),
    Output("date-slider", "step"),
    Output("date-slider", "marks"),
    Output("date-slider", "value", allow_duplicate=True),
    Input("storm-param-dropdown", "value"),
    prevent_initial_call=True
)
def adjust_slider_for_param(selected_param):
    """
    If 'rainy_days' is selected, base slider on month start/end 
    rather than exact min_date from storm dataset.
    """
    min_dt = pd.to_datetime(min_date)
    max_dt = pd.to_datetime(max_date)

    # --- Default (daily) slider ---
    if selected_param != "rainy_days":
        total_days = (max_dt - min_dt).days
        marks = {
            0: {"label": "Start", "style": {"color": "#0a4275", "fontWeight": "600"}},
            total_days: {"label": "End", "style": {"color": "#0a4275", "fontWeight": "600"}},
        }
        return 0, total_days, 1, marks, [0, total_days]

    # --- Monthly slider for Rainy Days ---
    months = pd.date_range(start=min_month, end=max_month, freq="MS")
    month_labels = {int((m - min_month).days): m.strftime("%b %Y") for m in months}
    month_steps = sorted(month_labels.keys())

    marks = {
        k: {"label": v, "style": {"color": "#0a4275", "fontWeight": "600"}}
        for k, v in month_labels.items()
    }

    step = month_steps[1] - month_steps[0] if len(month_steps) > 1 else 30

    return 0, month_steps[-1], step, marks, [0, month_steps[-1]]
    

@callback(
    Output("table-container", "children"),
    Output("page-info", "children"),
    Output("page-input", "value"),  # keep input synced
    Input("raw-data-store", "data"),
    Input("next-page", "n_clicks"),
    Input("prev-page", "n_clicks"),
    Input("page-input", "value"),  # NEW
    State("page-info", "children"),
    prevent_initial_call=True
)
def update_table(data, next_click, prev_click, page_value, page_info):
    if not data:
        msg = html.Div(
            "Please select a parameter and date range!",
            style={"textAlign": "center", "color": "#555", "fontWeight": "bold", "marginTop": "2rem", "fontSize": "1.2rem"}
        )
        return msg, dash.no_update, dash.no_update

    df = pd.read_json(data, orient="split")
    rows_per_page = 20
    total_pages = (len(df) - 1) // rows_per_page + 1

    # Determine current page
    ctx = dash.callback_context
    page = 0
    if page_info and "Page" in page_info:
        page = int(page_info.split()[1]) - 1

    if ctx.triggered_id == "next-page":
        page = min(page + 1, total_pages - 1)
    elif ctx.triggered_id == "prev-page":
        page = max(page - 1, 0)
    elif ctx.triggered_id == "page-input" and page_value:
        # user typed a page number
        page = min(max(page_value - 1, 0), total_pages - 1)

    # Slice the dataframe
    start = page * rows_per_page
    end = start + rows_per_page
    sliced_df = df.iloc[start:end]

    page_text = f"Page {page + 1} of {total_pages}"

    # Create AgGrid
    grid = AgGrid(
        rowData=sliced_df.to_dict("records"),
        columnDefs=[{"field": col} for col in sliced_df.columns],
        defaultColDef={"filter": True, "sortable": True, "resizable": True},
        style={"height": "500px", "width": "100%"}
    )

    return grid, page_text, page + 1  # sync the input value


# ----------------------------------------------------------
# 4. Core callback: Table + Plots
# ----------------------------------------------------------
@callback(
    Output("raw-storm-plot", "figure"),
    Output("cleaned-storm-plot", "figure"),
    Output("raw-data-store", "data"),
    Input("storm-param-dropdown", "value"),
    Input("date-slider", "value"),
    Input("page-loaded", "data"),
    prevent_initial_call=False
)
def update_table_and_plots(selected_param, slider_value, _):
    """Update table and plots when parameter/date changes, or show placeholder on first load."""
    start = time.time()     #-----------------------------TEST
    
    # ---- CASE 1: On first load or no parameter selected ----
    if not selected_param:
        placeholder_fig = go.Figure()
        placeholder_fig.add_annotation(
            text="Please select a parameter and date range!",
            showarrow=False,
            font=dict(size=16, color="#777"),
            xref="paper", yref="paper", x=0.5, y=0.5
        )
        placeholder_fig.update_layout(
            template="plotly_white",
            height=350,
            xaxis_visible=False,
            yaxis_visible=False
        )
        return placeholder_fig, placeholder_fig, None

    # ---- CASE 2: When parameter is selected ----
    if not slider_value:
        slider_value = [0, (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days]

    start_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[0], unit="D")
    end_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[1], unit="D")

    # --- Load raw data (always from queried_df)

    db = StormDatabase()
    df_raw = db.get_storm_profiles(start_date, end_date).copy()
    
    # Ensure outlier column is string for display
    if "outlier" in df_raw.columns:
        df_raw["outlier"] = df_raw["outlier"].astype(str)
    

    # Choose relevant columns based on parameter
    if selected_param == "storm_area_km2":
        columns_to_show = ["storm_id", "datetime", "storm_area_km2", "storm_centroid_lat", "storm_centroid_long", "outlier"]
    elif selected_param == "storm_distance_km":
        columns_to_show = ["storm_id", "datetime", "storm_distance_km", "storm_area_km2", "storm_centroid_lat", "storm_centroid_long", "outlier"]
    elif selected_param == "storm_duration_min":
        columns_to_show = ["storm_id", "datetime", "storm_duration_min", "storm_area_km2", "storm_centroid_lat", "storm_centroid_long", "outlier"]
    elif selected_param == "rainy_days":
        df_raw = db.get_rainy_days(start_date, end_date).copy()
        df_raw["date"] = pd.to_datetime(df_raw["date"])
        
        # Include any month that overlaps with the selected date range
        df_raw["month_start"] = df_raw["date"]
        df_raw["month_end"] = df_raw["date"] + pd.offsets.MonthEnd(0)
        df_raw = df_raw[
            (df_raw["month_start"] <= end_date) & (df_raw["month_end"] >= start_date)
        ]
        columns_to_show = ["date", "number_of_rainy_days"]
    else:
        # fallback
        columns_to_show = [c for c in df_raw.columns if c not in ["storm_centroid_x", "storm_centroid_y"]]

    columns_to_show = [c for c in columns_to_show if c in df_raw.columns]

    # Build Plots (aggregated, not raw)

    if selected_param == "storm_area_km2":
        df_raw_plot = db.get_aggregated_area(False, start_date, end_date)
        df_clean_plot = db.get_aggregated_area(True, start_date, end_date)
        xcol, ycol, title = "date", "average_storm_area_km2", "Average Storm Area Over Time"

    elif selected_param == "storm_distance_km":
        df_raw_plot = db.get_aggregated_distance(False, start_date, end_date)
        df_clean_plot = db.get_aggregated_distance(True, start_date, end_date)
        xcol, ycol, title = "date", "storm_distance_km", "Average Distance Travelled By Storms Over Time"

    elif selected_param == "storm_duration_min":
        df_raw_plot = db.get_aggregated_duration(False, start_date, end_date)
        df_clean_plot = db.get_aggregated_duration(True, start_date, end_date)
        xcol, ycol, title = "date", "storm_duration_min", "Average Storm Duration Over Time"

    elif selected_param == "rainy_days":
        df_raw_plot = storm_db.get_rainy_days(start_date, end_date).copy()
     
        fig = px.scatter(df_raw_plot, x="date", y="number_of_rainy_days", title="Rainy Days Over Time")
        fig.update_traces(mode="markers+lines")
        fig.update_layout(template="plotly_white")
        return fig, fig, df_raw_plot.to_json(date_format="iso", orient="split")


    else:
        return px.line(title="Invalid parameter"), px.line(title="Invalid parameter")
        
    # Build Raw + Cleaned Plots
    fig_raw = make_bestfit_plot(df_raw_plot, xcol, ycol, title + " (Raw)")
    fig_clean = make_bestfit_plot(df_clean_plot, xcol, ycol, title + " (Cleaned)")
    
    end = time.time()
    print("REG PLOT:", end-start)
    # Convert to JSON (safe for Dash)
    df_json = df_raw.to_json(date_format="iso", orient="split")
    
    return fig_raw, fig_clean, df_json  # <--- need to add Output for Store

# Helper for regression best-fit line
def make_bestfit_plot(df, xcol, ycol, title):
    if df.empty:
        return px.line(title=title + " — No data")
        
    start = time.time()   #---------------------------TEST
        
    df = df.dropna(subset=[xcol, ycol]).sort_values(xcol)
    x = pd.to_datetime(df[xcol])
    y = df[ycol]
    x_num = (x - x.min()).dt.total_seconds()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Data"))
        
    subtitle_text = ""
    if len(y) >= 2:
        coef = np.polyfit(x_num, y, 1)
        y_fit = np.polyval(coef, x_num)
        m, b = coef[0], coef[1]
        subtitle_text = f"Best Fit: y = {m:.4f}x + {b:.2f}"
        fig.add_trace(go.Scatter(
            x=x,
            y=y_fit,
            mode="lines",
            name="Best Fit Line",
            line=dict(color="red")
        ))

    # Define friendly axis labels with units
    y_labels = {
        "rainfall": "Rainfall (mm)",
        "wind_speed": "Wind Speed (m/s)",
        "temperature": "Temperature (°C)",
        "humidity": "Relative Humidity (%)",
        "average_storm_area_km2": "Area Coverage (km²)",
        "storm_distance_km": "Distance travelled (km)",
        "storm_duration_min": "Duration (min)"
    }

    # Use dictionary label or fallback
    yaxis_label = y_labels.get(ycol, ycol.replace("_", " ").title())
    
    # Add the subtitle just below the main title
    fig.update_layout(
        title={
            "text": f"{title}<br><sup>{subtitle_text}</sup>",
            "x": 0.5,
            "xanchor": "center"
        },
        yaxis_title=yaxis_label,
        template="plotly_white",
        height=320,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bordercolor="LightGray",
            borderwidth=1,
            font=dict(size=12)
        )
    )
    return fig


# ----------------------------------------------------------
# 5. Download CSV
# ----------------------------------------------------------
@callback(
    Output("download-raw", "data"),
    Input("download-raw-btn", "n_clicks"),
    State("storm-param-dropdown", "value"),
    State("date-slider", "value"),
    prevent_initial_call=True,
)
def download_raw_csv(n_clicks, selected_param, slider_value):
    if not n_clicks or not selected_param or not slider_value:
        raise dash.exceptions.PreventUpdate

    # Default daily params
    start_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[0], unit="D")
    end_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[1], unit="D")

    # Monthly adjustment for Rainy Days
    if selected_param == "rainy_days":
        start_date = min_month + pd.to_timedelta(slider_value[0], unit="D")
        end_date = min_month + pd.to_timedelta(slider_value[1], unit="D")

        db = StormDatabase()

        df = db.get_rainy_days(start_date, end_date).copy()
        df["date"] = pd.to_datetime(df["date"])

        # Include any month overlapping the selected range
        df["month_start"] = df["date"]
        df["month_end"] = df["date"] + pd.offsets.MonthEnd(0)
        df = df[(df["month_start"] <= end_date) & (df["month_end"] >= start_date)]

        filename = "rainy_days_raw.csv"
    else:
        # Default logic for other storm parameters
        db = StormDatabase()
        df = db.get_storm_profiles(start_date, end_date)
        df['outlier'] = df['outlier'].map({True: 'TRUE', False: 'FALSE'})
        
        filename = f"{selected_param}_raw.csv"

    df.columns = [c.lower() for c in df.columns]
    return dcc.send_data_frame(df.to_csv, filename, index=False)


@callback(
    Output("download-clean", "data"),
    Input("download-clean-btn", "n_clicks"),
    State("storm-param-dropdown", "value"),
    State("date-slider", "value"),
    prevent_initial_call=True,
)
def download_clean_csv(n_clicks, selected_param, slider_value):
    if not n_clicks or not selected_param or not slider_value:
        raise dash.exceptions.PreventUpdate

    # Default daily params
    start_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[0], unit="D")
    end_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[1], unit="D")

    # Monthly adjustment for Rainy Days
    if selected_param == "rainy_days":
        start_date = min_month + pd.to_timedelta(slider_value[0], unit="D")
        end_date = min_month + pd.to_timedelta(slider_value[1], unit="D")

        db = StormDatabase()

        df = db.get_rainy_days(start_date, end_date).copy()
        df["date"] = pd.to_datetime(df["date"])

        # Include any month overlapping the selected range
        df["month_start"] = df["date"]
        df["month_end"] = df["date"] + pd.offsets.MonthEnd(0)
        df = df[(df["month_start"] <= end_date) & (df["month_end"] >= start_date)]

        filename = "rainy_days_clean.csv"
    else:
        db = StormDatabase()
        df = db.get_storm_profiles(start_date, end_date).copy()

        # Filter out outliers
        if "outlier" in df.columns:
            df = df[df["outlier"] == False].drop(columns=["outlier"], errors="ignore")

        df = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
        filename = f"{selected_param}_clean.csv"

    df.columns = [c.lower() for c in df.columns]
    return dcc.send_data_frame(df.to_csv, filename, index=False)

# ----------------------------------------------------------
# 6. Page callbacks
# ----------------------------------------------------------
@callback(
    Output("storm-param-dropdown", "value"),
    Output("date-slider", "value"),
    Input("url", "search"),
)
def set_initial_filters(search):
    from urllib.parse import parse_qs
    if not search:
        raise dash.exceptions.PreventUpdate

    query = parse_qs(search.lstrip("?"))
    selected_param = query.get("param", [None])[0]
    start_date = query.get("start", [str(min_date)])[0]
    end_date = query.get("end", [str(max_date)])[0]

    # Convert to slider offsets (days from min_date)
    min_dt = pd.to_datetime(min_date)
    s_offset = (pd.to_datetime(start_date) - min_dt).days
    e_offset = (pd.to_datetime(end_date) - min_dt).days

    return selected_param, [s_offset, e_offset]

@callback(
    Output("storm-param-dropdown", "value", allow_duplicate=True),
    [
        Input("param-storm_area_km2", "n_clicks"),
        Input("param-storm_distance_km", "n_clicks"),
        Input("param-storm_duration_min", "n_clicks"),
        Input("param-rainy_days", "n_clicks"),
    ],
    prevent_initial_call=True
)
def select_param(btn1, btn2, btn3, btn4):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    clicked = ctx.triggered[0]["prop_id"].split(".")[0]
    mapping = {
        "param-storm_area_km2": "storm_area_km2",
        "param-storm_distance_km": "storm_distance_km",
        "param-storm_duration_min": "storm_duration_min",
        "param-rainy_days": "rainy_days"
    }
    return mapping.get(clicked)

# Shows active paramater
@callback(
    [
        Output("param-storm_area_km2", "color"),
        Output("param-storm_distance_km", "color"),
        Output("param-storm_duration_min", "color"),
        Output("param-rainy_days", "color"),
        Output("param-storm_area_km2", "outline"),
        Output("param-storm_distance_km", "outline"),
        Output("param-storm_duration_min", "outline"),
        Output("param-rainy_days", "outline"),
    ],
    Input("storm-param-dropdown", "value")
)
# Shows selected parameter
def highlight_selected_card(selected):
    # Default appearance
    color_default = "secondary"
    color_active = "success"

    return [
        color_active if selected == "storm_area_km2" else color_default,
        color_active if selected == "storm_distance_km" else color_default,
        color_active if selected == "storm_duration_min" else color_default,
        color_active if selected == "rainy_days" else color_default,
        False if selected == "storm_area_km2" else True,
        False if selected == "storm_distance_km" else True,
        False if selected == "storm_duration_min" else True,
        False if selected == "rainy_days" else True,
    ]

# Enables/Disables table legend
@callback(
    Output("legend-container", "style"),
    Output("toggle-legend-btn", "children"),
    Input("toggle-legend-btn", "n_clicks"),
)
def toggle_legend(n_clicks):
    # Default: show legend on page load
    if not n_clicks:
        return {"marginBottom": "10px"}, "Hide Legend"

    # Toggle visibility
    if n_clicks % 2 == 1:
        return {"display": "none"}, "Show Legend"
    else:
        return {"marginBottom": "10px"}, "Hide Legend"

# ----------------------------------------------------------
# 7. Fetch API Data
# ----------------------------------------------------------
@callback(
    Output("api-modal", "is_open"),
    Output("api-modal-body", "children"),
    Input("open-api-modal", "n_clicks"),
    Input("close-api-modal", "n_clicks"),
    State("storm-param-dropdown", "value"),
    State("date-slider", "value"),
    State("api-modal", "is_open"), 
    prevent_initial_call=True
)
def toggle_api_modal(open_click, close_click, selected_param, slider_value, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "close-api-modal":
        return False, dash.no_update

    if not selected_param:
        return True, html.Div("Please select a parameter first.", style={"color": "red"})

    # Convert slider to dates
    start_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[0], unit="D")
    end_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[1], unit="D")

    # Define endpoint mapping
    multi_endpoints = ["storm_area_km2", "storm_distance_km", "storm_duration_min"]
    single_endpoints = {
        "rainy_days": "get_rainy_days_data",
        "other_storm_features": "get_other_storm_data"
    }

    urls = []

    if selected_param in multi_endpoints:
        for suffix in ["raw", "clean"]:
            url = f"http://localhost:8050/api/frontend/get_{suffix}_storm_data?start_date={start_date.date()}&end_date={end_date.date()}"
            urls.append((suffix.capitalize(), url))
    elif selected_param in single_endpoints:
        url = f"http://localhost:8050/api/frontend/{single_endpoints[selected_param]}?start_date={start_date.date()}&end_date={end_date.date()}"
        urls.append(("Data", url))
    else:
        return True, html.Div("Invalid parameter selected.", style={"color": "red"})

    # Build HTML body
    body = html.Div([
        html.H5("This code can be used to test a sample API query.", style={"marginBottom": "10px"}),
        html.Div([
            html.Div([
                html.B(name + " URL:"),
                html.Pre(
                    f"""import requests\n\nurl = "{url}"\nresponse = requests.get(url)\nprint(response.json())""",
                    style={
                        "backgroundColor": "#0d1117",
                        "color": "#c9d1d9",
                        "fontFamily": "monospace",
                        "borderRadius": "6px",
                        "padding": "1rem",
                        "whiteSpace": "pre-wrap",
                        "marginBottom": "10px"
                    }
                ),
                html.P([
                    html.A(url, href=url, target="_blank", style={"color": "#0a4275", "fontWeight": "600"})
                ])
            ], style={"marginBottom": "15px"})
            for name, url in urls
        ])
    ])

    return not is_open, body

# ----------------------------------------------------------
# 8. Explanation of Mahalanobis distance and data parameters
# ----------------------------------------------------------
@callback(
    Output("info-modal", "is_open"),
    Input("info-icon", "n_clicks"),
    Input("close-info", "n_clicks"),
    State("info-modal", "is_open"),
)
def toggle_modal(open_click, close_click, is_open):
    if open_click or close_click:
        return not is_open
    return is_open

# ----------------------------------------------------------
# 9. Shows date range slider
# ----------------------------------------------------------
@callback(
    Output("slider-date-display", "children"),
    [Input("date-slider", "value"), Input("storm-param-dropdown", "value")],
    prevent_initial_call=False
)
def update_date_label(slider_value, selected_param):
    """Show readable range depending on parameter granularity."""
    # ---- Monthly (Rainy Days) ----
    if selected_param == "rainy_days":
        if not slider_value:
            slider_value = [0, (max_month - min_month).days]

        start_date = min_month + pd.to_timedelta(slider_value[0], unit="D")
        end_date = min_month + pd.to_timedelta(slider_value[1], unit="D")

        start_label = start_date.strftime("%b %Y")
        end_label = end_date.strftime("%b %Y")

        return f"Selected range: {start_label} → {end_label}"

    # ---- Daily (other storm parameters) ----
    if not slider_value:
        slider_value = [0, (pd.to_datetime(max_date) - pd.to_datetime(min_date)).days]

    start_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[0], unit="D")
    end_date = pd.to_datetime(min_date) + pd.to_timedelta(slider_value[1], unit="D")

    return f"Selected range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}"