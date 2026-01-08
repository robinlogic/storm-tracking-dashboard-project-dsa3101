from flask import Flask, jsonify, request, url_for, send_file
import posixpath
import pandas as pd
import io
from datetime import datetime, timedelta
from backend_ws.secrets.db import get_conn
from backend_ws.app.gcs import list_gcs_files, load_from_gcs
from backend_ws.app.config import RADAR_OUTPUT
from backend_ws.algorithm.aggregate import (
    compute_outliers,
    aggregate_area_by_interval,
    aggregate_distance_duration,
    pixels_to_latlon,
    compute_storm_metrics
)

app = Flask(__name__)

# --------------------------
# Proxy endpoint for a single radar image
# --------------------------
@app.route("/api/titan/radar_image", methods=["GET"])
def radar_image_proxy():
    gcs_path = request.args.get("gcs_path")
    if not gcs_path:
        return jsonify({"error": "Missing gcs_path"}), 400
    try:
        img_bytes = load_from_gcs(gcs_path)
        return send_file(io.BytesIO(img_bytes), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------
# Radar images + snapshot storm profiles endpoint
# --------------------------
@app.route("/api/titan/radar_images_storm_profiles", methods=["GET"])
def radar_images_storm_profiles():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    try:
        conn = get_conn()
        query = """
        SELECT storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y, outlier
        FROM storm_profiles_snapshot
        WHERE datetime >= %s AND datetime <= %s
        """
        df_snapshot = pd.read_sql(query, conn, params=[start_date, end_date])
        conn.close()

        if df_snapshot.empty:
            snapshot_profiles = []
        else:
            snapshot_profiles = df_snapshot.to_dict(orient="records")

        radar_prefix = posixpath.join(RADAR_OUTPUT, "70km")
        all_dates = pd.date_range(start=start_date, end=end_date).strftime("%Y%m%d")
        radar_files = []
        for date_str in all_dates:
            folder = posixpath.join(radar_prefix, date_str)
            files = list_gcs_files(folder)
            for f in files:
                proxy_url = request.host_url.rstrip("/") + url_for("radar_image_proxy") + f"?gcs_path={f}"
                radar_files.append(proxy_url)

        return jsonify({
            "radar_images": radar_files,
            "storm_profiles": snapshot_profiles
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Utility: parse start/end dates from request and extend end_date to end of day if no time
def parse_date_range(start_date_str, end_date_str):
    start_dt = pd.to_datetime(start_date_str)
    end_dt = pd.to_datetime(end_date_str)

    # If time is not specified (midnight), extend end to 23:59:59
    if end_dt.hour == 0 and end_dt.minute == 0 and end_dt.second == 0:
        end_dt = end_dt + pd.Timedelta(hours=23, minutes=59, seconds=59)

    return start_dt, end_dt


# --------------------------
# Storm area endpoint
# --------------------------
@app.route("/api/titan/storm_area", methods=["GET"])
def storm_area():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    interval = request.args.get("interval", "15T")

    try:
        start_dt, end_dt = parse_date_range(start_date, end_date)

        # Load snapshot storm profiles
        conn = get_conn()
        query = """
        SELECT storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y, outlier
        FROM storm_profiles_snapshot
        WHERE datetime >= %s AND datetime <= %s
        """
        snapshot_df = pd.read_sql(query, conn, params=[start_dt, end_dt])
        conn.close()

        if snapshot_df.empty:
            return jsonify({"error": "No storm data found"}), 404

        # Aggregated tables (using per-timestamp area for area endpoint)
        agg_all = aggregate_area_by_interval(snapshot_df, start_date=start_dt, end_date=end_dt, interval=interval)
        non_outlier_df = snapshot_df[snapshot_df['outlier'] == False]
        agg_no_outliers = aggregate_area_by_interval(non_outlier_df, start_date=start_dt, end_date=end_dt, interval=interval)

        return jsonify({
            "storm_profiles": snapshot_df.to_dict(orient="records"),
            "aggregated_all": agg_all.to_dict(orient="records"),
            "aggregated_no_outliers": agg_no_outliers.to_dict(orient="records")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------
# Storm distance/duration endpoint
# --------------------------
@app.route("/api/titan/storm_distance_duration", methods=["GET"])
def storm_distance_duration():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    interval = request.args.get("interval", "D")

    try:
        start_dt, end_dt = parse_date_range(start_date, end_date)

        conn = get_conn()
        # Fetch snapshot profiles
        snapshot_df = pd.read_sql(
            """
            SELECT storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y, outlier
            FROM storm_profiles_snapshot
            WHERE datetime >= %s AND datetime <= %s
            """,
            conn,
            params=[start_dt, end_dt]
        )

        # Daily precomputed aggregates
        daily_agg = pd.read_sql(
            """
            SELECT date, avg_area, total_distance_km, duration_min, has_outliers
            FROM storm_distance_duration_daily
            WHERE date BETWEEN %s AND %s
            ORDER BY date
            """,
            conn,
            params=[start_dt.date(), end_dt.date()]
        )
        conn.close()

        if interval.upper() == "D":
            agg_all = daily_agg[daily_agg['has_outliers']==True].copy()
            agg_no_outliers = daily_agg[daily_agg['has_outliers']==False].copy()
            
            # Drop 'has_outliers' before sending to client
            agg_all = agg_all.drop(columns=["has_outliers"])
            agg_no_outliers = agg_no_outliers.drop(columns=["has_outliers"])
        else:
            # Compute per-storm metrics and aggregate on demand
            metrics_df = compute_storm_metrics(snapshot_df)
            storm_outlier_map = snapshot_df[["storm_id", "outlier"]].drop_duplicates()
            metrics_df = metrics_df.merge(storm_outlier_map, on="storm_id", how="left")
        
            agg_all = aggregate_distance_duration(metrics_df, start_date=start_dt, end_date=end_dt, interval=interval)
            non_outlier_metrics = metrics_df[metrics_df["outlier"] == False]
            agg_no_outliers = aggregate_distance_duration(non_outlier_metrics, start_date=start_dt, end_date=end_dt, interval=interval)

        return jsonify({
            "storm_profiles": snapshot_df.to_dict(orient="records"),
            "aggregated_all": agg_all.to_dict(orient="records"),
            "aggregated_no_outliers": agg_no_outliers.to_dict(orient="records")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
