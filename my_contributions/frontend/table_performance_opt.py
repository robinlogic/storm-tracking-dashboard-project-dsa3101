"""
Storm Data Explorer Optimisation — Showcase Snippets

This file contains key code excerpts from `data_explorer.py` 
(under: storm_project/frontend_ws/app/pages) that I personally wrote 
to improve the performance and usability of the Data Explorer page.

Optimisations include:
1. Client-side caching using dcc.Store for session-long dataset storage.
2. Efficient slicing and manual pagination of large DataFrames for Dash AG Grid.
3. Decoupling data retrieval from rendering to reduce load times.

The full file is much longer; only the most relevant parts for performance 
optimisation are included here.
"""


# ----------------------------------------------------------
# Initialisation of dcc.Store for data cache (holds data for the entire session)
# ----------------------------------------------------------

dcc.Store(id="raw-data-store", storage_type="session"),
html.Div([
    ... ])
#################################



# ----------------------------------------------------------
# This function returns the dataframe in JSON format for the table to decode and display.
# ----------------------------------------------------------
@callback(
    ...
    Output("raw-data-store", "data"),
    ...
)
def update_table_and_plots(selected_param, slider_value, _):
    """Update table and plots when parameter/date changes, or show placeholder on first load."""
    
    start = time.time()     #----------- Table and plot loading time test
    ... 
    
    # --- Load raw data (always from queried_df)

    db = StormDatabase()
    df_raw = db.get_storm_profiles(start_date, end_date).copy() # Usage of data layer abstraction
    
    ...
    
    elif selected_param == "rainy_days":
        ...
        return fig, fig, df_raw_plot.to_json(date_format="iso", orient="split")
    else:
        return px.line(title="Invalid parameter"), px.line(title="Invalid parameter")
        
    ...

    end = time.time()

    print("REG PLOT:", end-start)  #----------- End of time test


    # Store full DataFrame in JSON to avoid sending raw pandas object to the frontend
    df_json = df_raw.to_json(date_format="iso", orient="split") 
    
    
    return fig_raw, fig_clean, df_json  # <--- need to add Output for Store



# ----------------------------------------------------------
# This function slices the dataframe given and paginates it for viewing.
# ----------------------------------------------------------

@callback(
    ...
    Input("raw-data-store", "data"),
    ...
)
def update_table(data, next_click, prev_click, page_value, page_info):
    if not data:
        msg = html.Div(
            "Please select a parameter and date range!",
            style={"textAlign": "center", "color": "#555", "fontWeight": "bold", "marginTop": "2rem", "fontSize": "1.2rem"}
        )
        return msg, dash.no_update, dash.no_update

    df = pd.read_json(data, orient="split")
    
    rows_per_page = 20 # Can be adjusted for performance vs usability
    
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


