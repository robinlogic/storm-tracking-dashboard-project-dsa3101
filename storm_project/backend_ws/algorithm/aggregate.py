import pandas as pd
import numpy as np
from scipy.spatial import distance
from sklearn.preprocessing import StandardScaler
from backend_ws.app.config import PROFILES_OUTPUT
from backend_ws.app.gcs import load_from_gcs, list_gcs_files, upload_to_gcs
from backend_ws.secrets.db import get_conn
import posixpath
from datetime import datetime

# --------------------------
# Helper: Pixel → lat/lon conversion
# --------------------------
def pixels_to_latlon(x_px, y_px, radar_lat_center=1.3521, radar_lon_center=103.8198,
                     radar_range_km=70, img_width_px=217, img_height_px=120):
    km_per_pixel_x = (2 * radar_range_km) / img_width_px
    km_per_pixel_y = (2 * radar_range_km) / img_height_px
    dx_km = (x_px - img_width_px / 2) * km_per_pixel_x
    dy_km = (y_px - img_height_px / 2) * km_per_pixel_y
    delta_lat = dy_km / 111
    delta_lon = dx_km / (111 * np.cos(np.radians(radar_lat_center)))
    return radar_lat_center + delta_lat, radar_lon_center + delta_lon


# --------------------------
# Compute outliers for a DataFrame using specified features
# --------------------------
def compute_outliers(df: pd.DataFrame, features=None):
    if df.empty or len(df) < 2:
        df["outlier"] = False
        return df

    if features is None:
        features = ["avg_area", "total_distance_km", "duration_min"]

    scaled = StandardScaler().fit_transform(df[features])
    scaled_df = pd.DataFrame(scaled, columns=features)

    cov_matrix = np.cov(scaled_df.values, rowvar=False)
    try:
        inv_cov = np.linalg.inv(cov_matrix)
    except np.linalg.LinAlgError:
        inv_cov = np.linalg.inv(cov_matrix + np.eye(cov_matrix.shape[0]) * 1e-6)

    mean_vec = scaled_df.mean().values
    distances = scaled_df.apply(lambda row: distance.mahalanobis(row, mean_vec, inv_cov), axis=1)
    threshold = distances.mean() + 3 * distances.std()
    df["outlier"] = distances > threshold
    return df


# --------------------------
# Compute per-storm metrics for outlier detection
# --------------------------
def compute_storm_metrics(df_snapshot: pd.DataFrame):
    if df_snapshot.empty:
        return pd.DataFrame(columns=["storm_id", "date", "avg_area", "total_distance_km", "duration_min"])

    df_snapshot = df_snapshot.copy()
    df_snapshot['date'] = df_snapshot['datetime'].dt.date

    metrics = []
    for (storm_id, date), group in df_snapshot.groupby(['storm_id', 'date']):
        group = group.sort_values('datetime')
        avg_area = group['storm_area'].mean()
        coords = group[['storm_centroid_x', 'storm_centroid_y']].values
        total_distance = np.sum(np.linalg.norm(coords[1:] - coords[:-1], axis=1))  # km units
        duration = (group['datetime'].max() - group['datetime'].min()).total_seconds() / 60.0
        metrics.append({
            'storm_id': storm_id,
            'date': date,
            'avg_area': avg_area,
            'total_distance_km': total_distance,
            'duration_min': duration
        })

    return pd.DataFrame(metrics)

# --------------------------
# Aggregate storm metrics monthly + compute outliers
# --------------------------
def compute_monthly_outliers():
    conn = get_conn()
    try:
        df = pd.read_sql("SELECT * FROM storm_profiles_snapshot", conn)
        if df.empty:
            print("[Outlier] No data in storm_profiles_snapshot.")
            conn.close()
            return

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["month"] = df["datetime"].dt.to_period("M").dt.to_timestamp()

        # --- Compute metrics per storm_id-month ---
        metrics = compute_storm_metrics(df)
        metrics["month"] = pd.to_datetime(metrics["date"]).dt.to_period("M").dt.to_timestamp()

        # --- Compute outliers per month ---
        all_outliers = []
        for month, group in metrics.groupby("month"):
            group_out = compute_outliers(group)
            all_outliers.append(group_out)
        metrics_out = pd.concat(all_outliers, ignore_index=True)

        # --- Update storm_profiles_snapshot with outlier flags ---
        cursor = conn.cursor()
        update_sql = """
            UPDATE storm_profiles_snapshot
            SET outlier = %s
            WHERE storm_id = %s
        """
        data = [(bool(row["outlier"]), row["storm_id"]) for _, row in metrics_out.iterrows()]
        cursor.executemany(update_sql, data)
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[Outlier] Monthly outlier flags updated in storm_profiles_snapshot ({len(data)} rows).")

    except Exception as e:
        print(f"[Outlier] Error computing monthly outliers: {e}")
        conn.close()

# --------------------------
# Aggregate storm area by interval
# --------------------------
def aggregate_area_by_interval(df: pd.DataFrame, start_date=None, end_date=None, interval="15T"):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"])

    if start_date:
        df = df[df["datetime"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["datetime"] <= pd.to_datetime(end_date)]

    df["interval_start"] = df["datetime"].dt.floor(interval)
    agg = df.groupby("interval_start")["storm_area"].mean().reset_index()
    return agg.rename(columns={"storm_area": "average_storm_area"})


# --------------------------
# Aggregate storm distance/duration by interval
# --------------------------
def aggregate_distance_duration(df_metrics: pd.DataFrame, start_date=None, end_date=None, interval="D"):
    if df_metrics.empty:
        return pd.DataFrame()

    df_metrics = df_metrics.copy()
    if start_date:
        df_metrics = df_metrics[df_metrics['date'] >= pd.to_datetime(start_date).date()]
    if end_date:
        df_metrics = df_metrics[df_metrics['date'] <= pd.to_datetime(end_date).date()]

    interval_upper = interval.upper()
    if interval_upper in ["D", "DAY"]:
        df_metrics["interval_start"] = pd.to_datetime(df_metrics["date"])
    elif interval_upper in ["W", "WEEK"]:
        # Week starting on Monday
        df_metrics["interval_start"] = pd.to_datetime(df_metrics["date"]) - pd.to_timedelta(pd.to_datetime(df_metrics["date"]).dt.weekday, unit='d')
    elif interval_upper in ["M", "MONTH"]:
        df_metrics["interval_start"] = pd.to_datetime(df_metrics["date"]).dt.to_period("M").dt.start_time
    else:
        raise ValueError("Interval must be 'day', 'week', or 'month'")

    agg = df_metrics.groupby("interval_start")[["avg_area", "total_distance_km", "duration_min"]].mean().reset_index()
    return agg.rename(columns={
        "avg_area": "average_storm_area",
        "total_distance_km": "average_storm_distance",
        "duration_min": "average_storm_duration"
    })


# --------------------------
# Precompute snapshot storm profiles from tracked_storms (for scheduler)
# --------------------------
from backend_ws.app.gcs import upload_to_gcs

def precompute_snapshot_profiles(date_str: str):
    """
    Generate snapshot storm profiles for a given date, insert into DB,
    and upload CSV to GCS (PROFILES_OUTPUT).
    Generates storm_id as "{original_storm_id}_{YYYYMMDD}".
    Columns: storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y
    """
    try:
        conn = get_conn()
        query = """
        SELECT storm_id AS original_storm_id, timestamp, x_pixels, y_pixels, storm_area_km2
        FROM storm_tracks
        WHERE DATE(timestamp) = %s
        """
        df = pd.read_sql(query, conn, params=[date_str])
        if df.empty:
            conn.close()
            return None

        # Compute centroids
        lat_lon = df.apply(lambda row: pixels_to_latlon(row.x_pixels, row.y_pixels), axis=1)
        df["storm_centroid_x"] = [c[0] for c in lat_lon]
        df["storm_centroid_y"] = [c[1] for c in lat_lon]
        df.rename(columns={"timestamp": "datetime", "storm_area_km2": "storm_area"}, inplace=True)

        # Generate daily-unique storm_id
        df['storm_id'] = df['original_storm_id'].astype(str) + '_' + pd.to_datetime(df['datetime']).dt.strftime('%Y%m%d')

        # Insert into DB
        insert_sql = """
        INSERT INTO storm_profiles_snapshot
        (storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y, outlier)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            storm_area=VALUES(storm_area),
            storm_centroid_x=VALUES(storm_centroid_x),
            storm_centroid_y=VALUES(storm_centroid_y)
        """
        cursor = conn.cursor()
        data = [
            (row.storm_id, row.datetime, row.storm_area, row.storm_centroid_x, row.storm_centroid_y, False)
            for _, row in df.iterrows()
        ]
        cursor.executemany(insert_sql, data)
        conn.commit()
        cursor.close()
        conn.close()

        # --- Upload CSV to GCS ---
        csv_bytes = df.to_csv(index=False)
        gcs_path = posixpath.join(PROFILES_OUTPUT, f"storm_profiles_{date_str}.csv")
        upload_to_gcs(csv_bytes, gcs_path)
        print(f"[Snapshot Precompute] Uploaded snapshot profiles to {gcs_path}")

        return df

    except Exception as e:
        print(f"[Snapshot Precompute] Error: {e}")
        return None

# --------------------------
# Precompute daily aggregated storm area
# --------------------------
def precompute_daily_storm_area(start_date, end_date):
    conn = get_conn()
    try:
        # Fetch snapshot profiles in range
        df = pd.read_sql(
            """
            SELECT storm_id, datetime, storm_area, outlier
            FROM storm_profiles_snapshot
            WHERE DATE(datetime) BETWEEN %s AND %s
            """,
            conn,
            params=[start_date, end_date]
        )
        if df.empty:
            print("[Precompute] No snapshot profiles found.")
            conn.close()
            return

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.date

        # Compute daily average storm area
        agg_all = df.groupby("date")["storm_area"].mean().reset_index().rename(
            columns={"storm_area": "average_storm_area"}
        )
        agg_no_outliers = df[df["outlier"] == False].groupby("date")["storm_area"].mean().reset_index().rename(
            columns={"storm_area": "average_storm_area"}
        )

        # Insert/update into table 'storm_area_daily'
        cursor = conn.cursor()
        insert_sql = """
        INSERT INTO storm_area_daily (date, average_storm_area, has_outliers)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            average_storm_area=VALUES(average_storm_area),
            has_outliers=VALUES(has_outliers)
        """
        data_all = [(row["date"], row["average_storm_area"], True) for _, row in agg_all.iterrows()]
        data_no_outliers = [(row["date"], row["average_storm_area"], False) for _, row in agg_no_outliers.iterrows()]

        cursor.executemany(insert_sql, data_all + data_no_outliers)
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[Precompute] Daily storm area aggregated for {len(agg_all)} days.")

    except Exception as e:
        print(f"[Precompute] Error: {e}")
        conn.close()


# --------------------------
# Precompute daily aggregated storm distance & duration
# --------------------------
def precompute_daily_distance_duration(start_date, end_date):
    conn = get_conn()
    try:
        # Fetch snapshot profiles with outliers
        df = pd.read_sql(
            """
            SELECT storm_id, datetime, storm_area, storm_centroid_x, storm_centroid_y, outlier
            FROM storm_profiles_snapshot
            WHERE DATE(datetime) BETWEEN %s AND %s
            """,
            conn,
            params=[start_date, end_date]
        )
        if df.empty:
            print("[Precompute] No snapshot profiles found.")
            conn.close()
            return

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.date

        # Compute per-storm metrics
        metrics = []
        for storm_id, group in df.groupby("storm_id"):
            group = group.sort_values("datetime")
            avg_area = group["storm_area"].mean()
            coords = group[["storm_centroid_x", "storm_centroid_y"]].values
            total_distance = np.sum(np.linalg.norm(coords[1:] - coords[:-1], axis=1))
            duration_min = (group["datetime"].max() - group["datetime"].min()).total_seconds() / 60.0
            outlier_flag = group["outlier"].iloc[0]  # outlier flag already precomputed
            metrics.append({
                "storm_id": storm_id,
                "avg_area": avg_area,
                "total_distance_km": total_distance,
                "duration_min": duration_min,
                "outlier": outlier_flag,
                "date": group["datetime"].dt.date.iloc[0]
            })

        metrics_df = pd.DataFrame(metrics)

        # Aggregate daily
        agg_all = metrics_df.groupby("date")[["avg_area", "total_distance_km", "duration_min"]].mean().reset_index()
        agg_no_outliers = metrics_df[metrics_df["outlier"] == False].groupby("date")[["avg_area", "total_distance_km", "duration_min"]].mean().reset_index()

        # Insert/update into table 'storm_distance_duration_daily'
        cursor = conn.cursor()
        insert_sql = """
        INSERT INTO storm_distance_duration_daily
        (date, avg_area, total_distance_km, duration_min, has_outliers)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            avg_area=VALUES(avg_area),
            total_distance_km=VALUES(total_distance_km),
            duration_min=VALUES(duration_min),
            has_outliers=VALUES(has_outliers)
        """

        data_all = [(row["date"], row["avg_area"], row["total_distance_km"], row["duration_min"], True) for _, row in agg_all.iterrows()]
        data_no_outliers = [(row["date"], row["avg_area"], row["total_distance_km"], row["duration_min"], False) for _, row in agg_no_outliers.iterrows()]

        cursor.executemany(insert_sql, data_all + data_no_outliers)
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[Precompute] Daily storm distance/duration aggregated for {len(agg_all)} days.")

    except Exception as e:
        print(f"[Precompute] Error: {e}")
        conn.close()
