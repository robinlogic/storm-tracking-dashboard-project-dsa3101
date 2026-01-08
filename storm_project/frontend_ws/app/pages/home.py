from dash import html, register_page, Input, Output, State, callback, dcc
import dash_bootstrap_components as dbc

register_page(__name__, path="/")

min_date = "2025-07-01"
max_date = "2025-10-31"

# ---------- Features ----------
features = [
    ("Storm Area", "bi bi-clouds", "storm_area_km2"),
    ("Storm Distance", "bi bi-compass", "storm_distance_km"),
    ("Storm Duration", "bi bi-clock", "storm_duration_min"),
    ("Rainy Days", "bi bi-cloud-rain", "rainy_days"),
    ("Storm Dynamics", "bi bi-cloud-haze2", "storm-tracking-map"),
]

cards = []

# Sample data trends
storm_summaries = {
    "Storm Area": "Between Aug and Oct 2025, average storm area stayed almost constant (0% change) at 62.52 km².",
    "Storm Distance": "Between Aug and Oct 2025, storm path lengths stayed almost constant at 0.06 km.",
    "Storm Duration": "Between Aug and Oct 2025, storm duration stayed almost constant at 5.22 min.",
    "Rainy Days": "Rainy days dropped by 7.14% from Aug to Sep 2025.", 
    "Storm Dynamics": "Visualise storm movements and their interactions with local weather and geographical features on a Map."
}

# Sample explanation of trends
storm_tooltips = {
    "Storm Area": html.Span([
        "Reflects the percentage change in average storm coverage area (km²) between periods of time (e.g., 2010 vs 2025).",
        html.Br(),
        html.I("(Current available data: 01-08-2025 to 31-10-2025.)")
    ]),
    "Storm Distance": html.Span([
        "Represents the relative change in average storm travel distance (km) between early and recent years (e.g., 2010 vs 2025).",
        html.Br(),
        "The values are derived from centroid displacement using the Haversine formula across sequential radar captures.",
        html.Br(),
        html.I("(Current available data: 01-08-2025 to 31-10-2025.)")
    ]),
    "Storm Duration": html.Span([
        "Shows how the average storm lifespan (minutes) has evolved, by comparing the mean duration per storm cell between earlier and later years (e.g., 2010 vs 2025).",
        html.Br(),
        "Computed from the temporal span between each storm’s start and end timestamps.",
        html.Br(),
        html.I("(Current available data: 01-08-2025 to 31-10-2025.)")
    ]),
    "Rainy Days": html.Span([
        "Indicates the change in the annual total number of rainy days, based on monthly radar-derived precipitation counts aggregated across Singapore between different months.",
        html.Br(),
        html.I("(Current available data: Aug 2025 to Sep 2025.)")
    ]),
    "Storm Dynamics": html.Span([
        "This section visualises storms over time across geographic regions, overlaying temperature, relative humidity, and wind vectors. By combining storm tracks with local weather conditions, users can explore patterns, identify potential intensification areas, and generate hypotheses about storm behaviour and interactions with the environment.",
        html.Br(),
        html.I("(Current avaliable data: 17-10-2025 11:00 to 17-10-2025 16:00.)")
               ])
}

methodology_section = html.Details(
    [
        html.Summary(
            ["Methodology ",
            html.I(className="bi bi-caret-down-fill")],
            style={
                "fontWeight": "600",
                "color": "#0a4275",
                "fontSize": "1.25rem",
                "cursor": "pointer",
                "listStyle": "none",
                "outline": "none",
            },
        ),
        html.Div([
            html.P(
                "Each storm in this project is assigned a unique Storm ID based on the day it occurs. "
                "As a result, a single storm that spans across midnight will be treated as two separate storms. "
                "This approach simplifies daily data aggregation but may split longer storm systems.",
                style={"fontSize": "0.85rem", "lineHeight": "1.6", "color": "#333"},
            ),
            html.P(
                "Future developers can enhance this logic to enable continuous storm tracking across multiple days, "
                "allowing better representation of long-lived storm systems. "
                "Additionally, storms that both form and dissipate within the currently visible time window are "
                "labelled in the Storm Tracking Map to help distinguish localised systems.",
                style={"fontSize": "0.85rem", "lineHeight": "1.6", "color": "#333"},
            ),
            html.P(
                "The storm cell tracking algorithm is adapted from the TITAN framework. For each storm ID, its position "
                "is predicted for the next timestamp. The same storm ID is then assigned to a newly detected storm cell "
                "if that cell’s position is the closest to the predicted location and lies within a 20 px radius.",
                style={
                    "fontSize": "0.85rem",
                    "lineHeight": "1.6",
                    "color": "#333",
                    "marginBottom": "0.8rem",
                },
            ),
            html.P(
                "It is also important to note that storm merging and splitting events are not yet resolved in this version. "
                "Split storms are treated as separate entities in the dataset. "
                "Merged storms are not explicitly recognised - if two storms are detected to hit the same spot, one is considered to "
                "have dissipated and while the other lives on, depending on which one's predicted position was closer.",
                style={
                    "fontSize": "0.85rem",
                    "lineHeight": "1.6",
                    "color": "#333",
                    "marginBottom": "0.8rem",
                },
            ),
        ],
            style={
                "marginTop": "0.8rem",
                "paddingLeft": "0.5rem"
            })
    ],
    style={
        "backgroundColor": "white",
        "padding": "1rem",
        "borderRadius": "10px",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
        "width": "100%",
        "marginTop": "1rem",
    },
)

# ---------- Create Cards + Modals ----------
for i, (title, icon, param) in enumerate(features):
    card = dcc.Link(
        dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.I(
                        className=f"{icon} text-primary",
                        style={"fontSize": "30px", "marginBottom": "0.3rem"}
                    ),
                    html.H4(
                        title,
                        style={
                            "fontWeight": "700",
                            "color": "#0a4275",
                            "margin": "0",
                            "fontSize": "1rem",
                            "textAlign": "center"
                        }
                    ),
                ], style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "height": "100%",
                    "width": "100%"
                })
            ]),
            style={
                "height": "100%",
                "width": "100%",
                "padding": "0.1rem 0.15rem",
                "boxShadow": "2px 2px 8px rgba(0,0,0,0.08)",
                "borderRadius": "12px",
                "borderTop": "4px solid #0a4275",
                "background": "#ffffff",
                "cursor": "pointer",
                "transition": "transform 0.15s ease, box-shadow 0.15s ease"
            },
            className="hover-card"
        ),
        href=f"/data-explorer?param={param}&start={min_date}&end={max_date}" if param != "storm-tracking-map" else "/storm-tracking-map",
        style={"textDecoration": "none", "width": "100%"}
    )
    cards.append(card)

# ---------- Page Layout ----------
layout = html.Div([
    html.Div([
        html.H1(
            "Storm Tracking Project",
            style={
                "color": "#0a4275",
                "fontWeight": "800",
                "marginBottom": "0.4rem",
                "fontSize": "2.6rem",
                "textAlign": "center"
            }
        ),
        html.P(
            "Explore key storm parameters in a single glance.",
            style={
                "textAlign": "center",
                "fontSize": "1.05rem",
                "color": "#555",
                "marginBottom": "1rem"
            }
        )
    ]),

    # === Main section ===
    dbc.Container([
        dbc.Row([
            # --- Summary ---
            dbc.Col([
                html.Div([
                    html.H5("Project Overview", style={
                        "fontWeight": "600",
                        "color": "#0a4275",
                        "marginBottom": "0.8rem"
                    }),
                    html.P(
                        "This dashboard summarises Singapore’s storm tracking analysis across multiple storm features. "
                        "It visualises how storm coverage, duration, and rainfall patterns have evolved over time, "
                        "helping to show climate trends in the longer term.",
                        style={
                            "fontSize": "0.85rem",
                            "lineHeight": "1.6",
                            "color": "#333"
                        }
                    ),
                    html.P(html.I("(Click on the cards on the right to explore the storm features.)"),
                        style={
                            "fontSize": "0.85rem",
                            "lineHeight": "1.6",
                            "color": "#333", 
                            "marginBottom": "0.8rem"
                        }
                    ),

                    html.Br(),
            
                    # --- Trends in Data ---
                    html.Div([
                        html.H5("Trends in Data (Aug to Oct 2025)", style={
                            "color": "#0a4275",
                            "fontWeight": "600",
                            "marginBottom": "0.8rem"
                        }),
                        html.Div([
                            html.Div([
                                html.H6(title, style={
                                    "color": "#0a4275",
                                    "fontWeight": "700",
                                    "marginBottom": "0.2rem",
                                    "fontSize": "0.95rem"
                                }),
                                html.P(storm_summaries[title], style={
                                    "fontSize": "0.85rem",
                                    "lineHeight": "1.5",
                                    "color": "#333",
                                    "marginBottom": "0.4rem"
                                })
                            ]) for title in storm_summaries.keys()
                        ])
                    ]),

                    methodology_section,
        
                    # --- More Feature Details as expandable card with fixed height ---
                    html.Details([
                        html.Summary([
                        "More Feature Details ",
                        html.I(className="bi bi-caret-down-fill")
                        ], style={
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "fontSize": "1.25rem", 
                            "color": "#0a4275",
                            "listStyle": "none",
                            "outline": "none"
                        }),
                        html.Div([
                            html.Div([
                                html.H6(title, style={
                                    "color": "#0a4275",
                                    "fontWeight": "700",
                                    "marginBottom": "0.2rem",
                                    "fontSize": "0.9rem"
                                }),
                                html.P(storm_tooltips[title], style={
                                    "fontSize": "0.85rem",
                                    "lineHeight": "1.5",
                                    "color": "#333",
                                    "marginBottom": "0.5rem"
                                })
                            ]) for title in storm_tooltips.keys()
                        ], style={
                            "marginTop": "0.8rem",       # match methodology spacing
                            "paddingLeft": "0.5rem"      # same as methodology content block
                        })
                    ], style={
                        "backgroundColor": "white",
                        "padding": "1rem",               # same as methodology_section
                        "borderRadius": "10px",
                        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                        "width": "100%",
                        "marginTop": "1rem",
                    })

                ], style={
                    "backgroundColor": "#ffffff",
                    "padding": "1.5rem",
                    "borderRadius": "14px",
                    "boxShadow": "2px 2px 12px rgba(0,0,0,0.1)",
                    "flex": "1",
                    "overflowY": "auto",
                    "maxHeight": "calc(105vh - 180px)",
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "flex-start",
                    "scrollbarWidth": "thin",
                })
            ], xs=12, sm=12, md=7, lg=8, xl=8, style={"minHeight": "0"}),

            # --- Five vertical cards ---
            dbc.Col([
                html.Div([
                    html.Div(
                        card,
                        style={
                            "flex": "1 1 0",      # allow grow/shrink equally
                            "width": "100%",
                            "marginBottom": "0.4rem"
                        }
                    ) for card in cards
                ], style={
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "space-evenly",
                    "alignItems": "stretch",
                    "gap": "0.4rem",
                    "height": "90%"
                })
            ], xs=12, sm=12, md=5, lg=4, xl=4, style={"minHeight": "0"})
        ],
        align="stretch",
        justify="between",
        style={
            "display": "flex",
            "height": "calc(110vh - 150px)",
            "minHeight": "0"
        })
    ], fluid=True, style={
        "maxWidth": "1300px",
        "paddingBottom": "1rem",
        "height": "100%"
    })
],
style={
    "backgroundColor": "#f2f3f4",
    "minHeight": "100vh",
    "padding": "1rem 2rem",
    "boxSizing": "border-box"
})


@callback(
    Output("collapse-details", "is_open"),
    Input("toggle-details", "n_clicks"),
    State("collapse-details", "is_open")
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open
