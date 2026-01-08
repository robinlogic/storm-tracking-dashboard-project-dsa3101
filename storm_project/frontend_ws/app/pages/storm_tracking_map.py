import os
import re
import base64
import numpy as np
import pandas as pd
import dash
from dash import html, dcc, register_page, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime
from storm_database import StormDatabase  

register_page(__name__, path="/storm-tracking-map")

# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
#DB_URL = "mysql+pymysql://root:dsa3101@127.0.0.1:5002/storm_features"

# Create DB object
storm_db = StormDatabase()

start_date = "2025-10-17 11:00:00"
end_date = "2025-10-17 16:00:00"

# ------------------------------------------------------------
# Helper: Get radar images from DB
# ------------------------------------------------------------
def list_radar_images_from_db(radar_range):
    # Call original method
    res = storm_db.get_radar_images(start_date, end_date)
    if res is None:
        print("No radar results returned from database.")
        return []

    df = res
    if df.empty:
        print("Radar table returned empty DataFrame.")
        return []

    # Filter by range
    range_col = "range" if "range" in df.columns else "radar_range" if "radar_range" in df.columns else None
    if range_col:
        df = df[df[range_col] == radar_range]

    df = df.sort_values("datetime").reset_index(drop=True)

    images = []
    for _, row in df.iterrows():
        dt_val = row["datetime"]

        # Clean and resolve the file path
        filename = row["image_path"].replace("\r", "").replace("\n", "").strip()

        # Check if already full path, else build expected path
        if os.path.isabs(filename):
            image_path = filename
        else:
            # Try both possible radar folders
            possible_paths = [
                os.path.join(DATA_DIR, filename),
                os.path.join(DATA_DIR, "storm_radar_images_km70", filename),
                os.path.join(DATA_DIR, "storm_radar_images_km240", filename),
            ]
            image_path = next((p for p in possible_paths if os.path.exists(p)), possible_paths[0])
        
        # Skip missing files
        if not os.path.exists(image_path):
            print(f"File not found: {image_path}")
            continue

        # Append found image to list
        if isinstance(dt_val, datetime):
            label = dt_val.strftime("%Y-%m-%d %H:%M")
        else:
            label = str(dt_val)

        images.append({"label": label, "value": image_path})

    print(f"Successfully loaded {len(images)} radar image paths for range {radar_range}")
    return images

RADAR_CACHE = {}

def get_cached_radar_images(selected_range):
    if selected_range not in RADAR_CACHE:
        print(f"Loading radar images for {selected_range}")
        RADAR_CACHE[selected_range] = list_radar_images_from_db(selected_range)
    return RADAR_CACHE[selected_range]

# ------------------------------------------------------------
# Load storm coordinate data
# ------------------------------------------------------------
def load_titan_data():
    csv_path = os.path.join(DATA_DIR, "storm_map_showcase.csv")
    start_date = "2025-10-17 11:00:00"
    end_date = "2025-10-17 16:00:00"
    
    # Call original method
    res = storm_db.get_storm_profiles(start_date, end_date)
    return res

df_titan = load_titan_data()

df_features = storm_db.get_other_storm_features(start_date, end_date)


# ------------------------------------------------------------
# Layout
# ------------------------------------------------------------
layout = html.Div([
    # === Large Title 
    html.Div(
        [
            # Left: icon + main title
            html.Div(
                [
                    html.I(
                        className="bi bi-cloud-haze2",
                        style={"fontSize": "80px", "marginRight": "1rem", "marginBottom": "0"}
                    ),
                    html.H1(
                        "Storm Dynamics",
                        style={
                            "color": "#0a4275",
                            "fontWeight": "800",
                            "margin": "0", 
                            "fontSize": "2.9rem",
                        }
                    ),
                ],
                style={"display": "flex", "alignItems": "center"}
            ),
            
            # Right: subtitle
            html.Div(
                html.P([
                    "Study the effect of local weather and",
                    html.Br(),
                    "geographic conditions on storm patterns."
                ],
                    style={
                        "fontSize": "1.1rem",
                        "color": "#555",
                        "marginBottom": "0",
                        "textAlign": "left"
                    }
                ),
                style={"display": "flex", "flexDirection": "column", "justifyContent": "center"}
            )
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "flex-start",  # aligns everything to the left
            "gap": "2rem",                   # space between icon/title and subtitle
            "marginBottom": "5px",
            "paddingLeft": "5px"
        }
    ),
    # --- Top-right API Access button + modal ---
    html.Div([
        dbc.Button(
            "API Access",
            id="open-api-modal-map",
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
                dbc.ModalBody(id="api-modal-map-body"),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-api-modal-map", color="primary", className="ms-auto")
                )
            ], id="api-modal-map", is_open=False, size="lg", scrollable=True, backdrop="static")
    ]),

    # === Main content row: sidebar + map ===
    html.Div([
        # --- Left sidebar ---
        html.Div([
            # Play button + speed selector + current time box
            html.Div([
                # Row 1: Play button + speed selector
                html.Div([
                    dbc.Button("▶ Play", id="play-btn", color="primary", n_clicks=0, style={"fontSize": "14px", "width": "87px", "height": "40px", "lineHeight": "1"}),
                    dbc.RadioItems(
                        id="speed-selector",
                        options=[
                            {"label": "0.5x", "value": 0.5},
                            {"label": "1x", "value": 1},
                            {"label": "2x", "value": 2}
                        ],
                        value=1,
                        inline=True,  # keeps them horizontal
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "8px", "fontSize": "13px"}
                    )
                ], style={"display": "flex", "alignItems": "center", "gap": "15px"}),
            
                # Current time box
                html.Div(
                    id="current-time-box",
                    style={
                        "border": "2px solid #0a4275",
                        "borderRadius": "8px",
                        "padding": "6px 12px",
                        "textAlign": "center",
                        "fontWeight": "600",
                        "fontSize": "16px",
                        "color": "#0a4275",
                        "backgroundColor": "#eaf2f8",
                        "marginTop": "10px",
                        "width": "90%"
                    }
                ),

            ], style={"marginBottom": "15px"}),


            # Slider under controls
            html.Div(
                dcc.Slider(
                    id="time-slider",
                    min=0,
                    max=20,
                    step=1,
                    value=0,
                    marks={
                        0: {"label": "start", "style": {"textAlign": "center", "fontSize": "15px"}},
                        20: {"label": "end", "style": {"textAlign": "center", "fontSize": "15px"}}
                    },
                    tooltip={"always_visible": False}
                ),
                style={
                    "width": "100%",
                    "marginBottom": "20px",
                    "textAlign": "left"
                }
            ),

            # Storm summary
            html.Div(
                id="storm-summary",
                style={"textAlign": "center", "color": "#333", "fontSize": "15px", "marginTop": "10px"}
            ),

            # Legend
            html.Div([
                html.Div(
                    "Colour bar indicates relative storm intensity (mm/hr).",
                    style={"textAlign": "center", "color": "#666", "fontSize": "13px", "marginTop": "5px"}
                ),

                # Rain intensity colour boxes
                html.Div([
                    html.Div(style={"backgroundColor": "#b0f0ff", "width": "20px", "height": "20px"}),
                    html.Small("Very light rain (0.05–0.25)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                html.Div([
                    html.Div(style={"backgroundColor": "#00e600", "width": "20px", "height": "20px"}),
                    html.Small("Light–moderate rain (0.25–3.00)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                html.Div([
                    html.Div(style={"backgroundColor": "#ffff00", "width": "20px", "height": "20px"}),
                    html.Small("Moderate–heavy rain (3.00–12.00)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                html.Div([
                    html.Div(style={"backgroundColor": "#ff9900", "width": "20px", "height": "20px"}),
                    html.Small("Heavy rain (12.00–30.00)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                html.Div([
                    html.Div(style={"backgroundColor": "#ff0000", "width": "20px", "height": "20px"}),
                    html.Small("Very heavy rain / thunderstorm (30.00–100.00)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                html.Div([
                    html.Div(style={"backgroundColor": "#9900cc", "width": "20px", "height": "20px"}),
                    html.Small("Extreme / possible hail (100-150+)", style={"marginLeft": "8px"})
                ], style={"display": "flex", "alignItems": "center"}),

                # Wind vector legend
                html.Details([
                    html.Summary([
                        "Wind vector legend ",
                        html.I(className="bi bi-caret-down-fill")
                    ], style={
                        "fontWeight": "600",
                        "cursor": "pointer",
                        "listStyle": "none",
                        "marginBottom": "5px"
                    }),
                    html.Img(
                        src="/assets/wind_legend.png",
                        style={"width": "100%", "maxWidth": "200px", "display": "block", "marginTop": "5px"}
                    )
                ], style={
                    "backgroundColor": "white",
                    "padding": "8px 12px",
                    "borderRadius": "10px",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.2)",
                    "fontSize": "13px",
                    "color": "#333",
                    "marginTop": "10px",
                    "width": "fit-content"
                }),


                html.Div([
                    html.Small("Data obtained from: weather.gov.sg")
                ], style={"display": "flex", "alignItems": "right"}),

            ], style={
                "backgroundColor": "white",
                "padding": "8px 12px",
                "borderRadius": "10px",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.2)",
                "fontSize": "13px",
                "color": "#333"
            }),

            # Toggle button 
            html.Div([
                dbc.Checklist(
                    options=[{"label": "Show Temperature | Relative Humidity", "value": 1}],
                    value=[1],  
                    id="toggle-temp-rh",
                    switch=True,
                    inline=True,
                    label_style={"fontSize": "13px", "marginLeft": "5px"}
                )
            ], style={"marginTop": "15px", "textAlign": "center"}),

        ], style={
            "flex": "0 0 300px",
            "marginRight": "20px",
            "marginTop": "40px"
        }),

        # --- Right main map ---
        html.Div([
            dcc.Graph(id="storm-map", style={"height": "73vh", "width": "100%"}),
        ], style={"flex": "1"}),

    ], style={
        "display": "flex",
        "marginTop": "2px"
             }),

    # Interval for animation
    dcc.Interval(id="interval-timer", interval=1500, n_intervals=0, disabled=True)

], style={"backgroundColor": "#f2f3f4", "padding": "1.5rem"})



# ------------------------------------------------------------
# Slider & Animation
# ------------------------------------------------------------
@callback(
    Output("time-slider", "max"),
    Output("time-slider", "value"),
    Output("interval-timer", "disabled"),
    Output("play-btn", "children"),
    Output("interval-timer", "interval"),
    Output("play-btn", "color"),
    Input("interval-timer", "n_intervals"),
    Input("play-btn", "n_clicks"),
    Input("speed-selector", "value"),
    State("time-slider", "value"),
    State("time-slider", "max"),
    State("interval-timer", "disabled"),
    )
def manage_animation_and_slider(n_intervals, play_clicks, speed, current_val, max_val, disabled):
    selected_range = "70km"
    imgs = get_cached_radar_images(selected_range) 
    max_idx = len(imgs) - 1 if imgs else 0
    triggered = dash.callback_context.triggered_id
    
    # Start from 11:00 image 
    start_idx = 0
    for i, img in enumerate(imgs):
        if "11:00" in img["label"]:
            start_idx = i
            break
    
    # Convert speed to interval (ms)
    base_interval = 1500
    interval_ms = int(base_interval / speed)
    
    # --- Play/Pause Toggle ---
    if triggered == "play-btn":
        new_disabled = not disabled
        new_label = "⏸ Pause" if not new_disabled else "▶ Play"
        new_color = "danger" if not new_disabled else "primary"
        return max_idx, current_val, new_disabled, new_label, interval_ms, new_color

    # --- Speed Change ---
    elif triggered == "speed-selector":
        return max_idx, current_val, disabled, (
            "⏸ Pause" if not disabled else "▶ Play"
        ), interval_ms, (
            "danger" if not disabled else "primary"
        )
    
    # --- Auto-Slide ---
    elif triggered == "interval-timer" and not disabled and max_idx > 0:
        new_val = (current_val + 1) % (max_idx + 1)
        return max_idx, new_val, disabled, "⏸ Pause", interval_ms, "danger"
    
    # --- Initial Load ---
    return max_idx, start_idx, True, "▶ Play", interval_ms, "primary"


# ------------------------------------------------------------
# Map Display Logic
# ------------------------------------------------------------
@callback(
    Output("storm-map", "figure"),
    Output("storm-summary", "children"),
    Output("current-time-box", "children"),
    Input("time-slider", "value"),
    Input("toggle-temp-rh", "value"),
)
def update_map(selected_idx, toggle_temp_rh):
    show_temp_rh = bool(toggle_temp_rh)  # True if toggle is ON
    radar_range = "70km"
    imgs = get_cached_radar_images(radar_range)
    if not imgs:
        return go.Figure(), "No radar images available.", ""

    idx = min(selected_idx, len(imgs) - 1)
    image_path = imgs[idx]["value"]
    timestamp_label = imgs[idx]["label"]

    # Load image to get size
    with Image.open(image_path) as img:
        img_width, img_height = img.size  # pixels

    # Encode radar image
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    # Singapore geographic bounds
    lat_center, lon_center = 1.3184, 103.8413    

    # Set radar range 
    radar_km_long = 62
    # Shorter axis proportional to image aspect ratio
    radar_km_short = radar_km_long * img_height / img_width

    # Convert km to degrees
    dlat = radar_km_short / 111.0
    dlon = radar_km_long / (111.0 * np.cos(np.radians(lat_center)))

    # Compute image corner coordinates
    lat_min, lat_max = lat_center - dlat / 2, lat_center + dlat / 2
    lon_min, lon_max = lon_center - dlon / 2, lon_center + dlon / 2

    # Plot map
    fig = go.Figure()
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=lat_center+0.006, lon=lon_center),
            zoom=10.25,
            layers=[dict(
                sourcetype="image",
                source=f"data:image/png;base64,{encoded}",
                coordinates=[
                    [lon_min, lat_max],
                    [lon_max, lat_max],
                    [lon_max, lat_min],
                    [lon_min, lat_min],
                ],
                opacity=0.6,
                below=""
            )],
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="#f2f3f4",
        showlegend=False,
    )

    # Convert df_titan datetime column to pandas datetime
    df_titan["datetime"] = pd.to_datetime(df_titan["datetime"])
    target_time = pd.to_datetime(timestamp_label)

    # Filter for exact match
    df_titan_filtered = df_titan[df_titan["datetime"] == target_time].copy()
    df_features_filtered = df_features[df_features["datetime"] == target_time].copy()

    # Add wind vectors, temperature/RH cards (same as your previous logic)
    if not df_features_filtered.empty:
        for _, row in df_features_filtered.iterrows():
            lat = row["lat"]
            lon = row["lon"]

            hover_parts = [f"{row.station_name}"]
            if pd.notna(row.get("wind_speed")) and pd.notna(row.get("wind_direction")):
                speed = row["wind_speed"]
                direction_deg = row["wind_direction"]
                hover_parts.append(f"Wind: {speed:.1f} m/s @ {direction_deg}°")
                angle = np.radians((270 - direction_deg) % 360)
                arrow_len = 0.004 * speed
                dlat = arrow_len * np.sin(angle)
                dlon = arrow_len * np.cos(angle) / np.cos(np.radians(lat))
                lat_end = lat + dlat
                lon_end = lon + dlon
                fig.add_trace(go.Scattermapbox(
                    lat=[lat, lat_end],
                    lon=[lon, lon_end],
                    mode="lines",
                    line=dict(color="royalblue", width=2),
                    showlegend=False,
                    hovertext="<br>".join(hover_parts),
                    hoverinfo="text"
                ))
                fig.add_trace(go.Scattermapbox(
                    lat=[lat_end],
                    lon=[lon_end],
                    mode="markers",
                    marker=dict(size=8, color="royalblue", symbol="circle"),
                    hoverinfo="skip",
                    showlegend=False
                ))

            if show_temp_rh and pd.notna(row.get("temperature")) and pd.notna(row.get("relative_humidity")):
                card_text = f"🌡 {row['temperature']}°C | 💧 {row['relative_humidity']}%"
                fig.add_trace(go.Scattermapbox(
                    lat=[lat + 0.002],
                    lon=[lon + 0.002],
                    mode="markers",
                    marker=dict(size=60, color="white", opacity=0.7, symbol="square"),
                    hoverinfo="skip",
                    showlegend=False
                ))
                fig.add_trace(go.Scattermapbox(
                    lat=[lat + 0.002],
                    lon=[lon + 0.002],
                    mode="markers+text",
                    marker=dict(size=0),
                    text=[card_text],
                    textposition="top right",
                    textfont=dict(size=10, color="black"),
                    hoverinfo="skip",
                    showlegend=False
                ))

    # Add TITAN storm centroids
    if not df_titan_filtered.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_titan_filtered["storm_centroid_lat"],
            lon=df_titan_filtered["storm_centroid_long"],
            mode="markers",
            marker=dict(size=2, color="red", opacity=0.3),
            hovertemplate=(
                "Storm ID: %{customdata[0]}<br>"
                "Lat: %{lat:.3f}<br>"
                "Lon: %{lon:.3f}<br>"
                "Area: %{customdata[1]} km²<extra></extra>"
            ),
            customdata=df_titan_filtered[["storm_id", "storm_area_km2"]].values
        ))

    # --- Storm summary with permanent info icon ---
    summary_text = f"🌀 {len(df_titan_filtered)} storm centers present." if not df_titan_filtered.empty else "No storm coordinates available."

    summary_div = html.Div([
        html.I(className="bi bi-info-circle", id="storm-info-icon", style={
            "fontSize": "18px",  # control size
            "color": "#0a4275",
            "marginRight": "8px",
            "cursor": "pointer"
        }),
        html.Span(summary_text, style={"color": "#333"})
    ], style={"display": "inline-flex", "alignItems": "center", "fontSize": "15px"})
    
    tooltip = dbc.Tooltip(
        "Hover over storm centres (identified with 'Storm ID') to know more information like their area coverage in km² at that timestamp.",
        target="storm-info-icon",
        placement="left"
    )

    date_str, time_str = timestamp_label.split(" ")
    display_box = f"📅 {date_str}   🕓 {time_str}"

    return fig, html.Div([summary_div, tooltip]), display_box


# ----------------------------------------------------------
# 7. Fetch API Data
# ----------------------------------------------------------
@callback(
    Output("api-modal-map", "is_open"),
    Output("api-modal-map-body", "children"),
    Input("open-api-modal-map", "n_clicks"),
    Input("close-api-modal-map", "n_clicks"),
    State("api-modal-map", "is_open"), 
    prevent_initial_call=True
)
def toggle_api_modal(open_click, close_click, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "close-api-modal":
        return False, dash.no_update

    # Define endpoint mapping
    multi_endpoints = ["storm_area_km2", "storm_distance_km", "storm_duration_min"]
    single_endpoints = {
        "rainy_days": "get_rainy_days_data",
        "other_storm_features": "get_other_storm_data"
    }
    urls = []
    url = f"http://localhost:8050/api/frontend/{single_endpoints['other_storm_features']}?start_date={start_date}&end_date={end_date}"
    urls.append(("Temperature, Relative Humidity, Wind Direction and Speed", url))

    url = f"http://localhost:8050/api/frontend/get_raw_storm_data?start_date={start_date}&end_date={end_date}"
    urls.append(("Storm profiles (Raw)", url))
    
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