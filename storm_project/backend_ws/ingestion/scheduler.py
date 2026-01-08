# backend_ws/ingestion/scheduler_full_pipeline.py

from datetime import datetime, timedelta
import traceback

from backend_ws.ingestion.fetch_radar import fetch_next_radar_for_timestamp
from backend_ws.ingestion.fetch_weather import fetch_weather_for_timestamps
from backend_ws.algorithm.titan import process_radar_for_titan
from backend_ws.algorithm.titan_tracking import track_storms_for_date
from backend_ws.algorithm.aggregate import (
    precompute_snapshot_profiles,
    precompute_daily_storm_area,
    precompute_daily_distance_duration
)
from backend_ws.app.config import RANGE_KM_VALUES

# --------------------------
# Scheduler Configuration
# --------------------------
CATCHUP_DAYS = 3

# --------------------------
# Upload all radar images for a day
# --------------------------
def upload_radar_images_for_day(date_obj):
    start_ts = datetime(date_obj.year, date_obj.month, date_obj.day)
    all_storm_timestamps = []

    for minute_offset in range(0, 24*60, 5):
        ts = start_ts + timedelta(minutes=minute_offset)
        for rng in RANGE_KM_VALUES:
            try:
                storm_ts = fetch_next_radar_for_timestamp(ts)
                if storm_ts:
                    all_storm_timestamps.extend(storm_ts)
            except Exception:
                print(f"[ERROR] Failed fetching radar for {ts}")
                traceback.print_exc()

    # Fetch weather for all timestamps
    if all_storm_timestamps:
        try:
            fetch_weather_for_timestamps(all_storm_timestamps)
        except Exception:
            print(f"[ERROR] Failed fetching weather for {date_obj}")
            traceback.print_exc()

    return all_storm_timestamps

# --------------------------
# Run pipeline including storm profile precomputation + outliers + daily aggregates
# --------------------------
def run_pipeline_for_day(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"\n=== [DAY] Processing {date_str} ===")

    try:
        # 1️⃣ Upload radar images and fetch weather
        upload_radar_images_for_day(date_obj)

        # 2️⃣ Process radar images via Titan
        process_radar_for_titan(date_str)

        # 3️⃣ Track storms
        track_storms_for_date(date_str)

        # 4️⃣ Precompute storm profiles (store in GCS & optionally SQL)
        metrics_df = precompute_snapshot_profiles(date_str)
        if metrics_df is not None:
            print(f"[INFO] Precomputed {len(metrics_df)} storm profiles for {date_str}")
        else:
            print(f"[INFO] No storm profiles to precompute for {date_str}")

        # 5️⃣ Compute monthly outliers
        from backend_ws.algorithm.aggregate import compute_monthly_outliers
        compute_monthly_outliers()
        print(f"[INFO] Monthly outliers updated")

        # 6️⃣ Precompute daily aggregated tables
        precompute_daily_storm_area(start_date=date_str, end_date=date_str)
        precompute_daily_distance_duration(start_date=date_str, end_date=date_str)
        print(f"[INFO] Daily aggregated tables updated for {date_str}")

    except Exception:
        print(f"[ERROR] Failed pipeline for {date_str}")
        traceback.print_exc()


# --------------------------
# Initial catch-up
# --------------------------
if __name__ == "__main__":
    print(f"[{datetime.now()}] Initial catch-up started for past {CATCHUP_DAYS} days")
    for day_offset in range(CATCHUP_DAYS, 0, -1):
        date_obj = datetime.today() - timedelta(days=day_offset)
        run_pipeline_for_day(date_obj)
    print(f"[{datetime.now()}] Initial catch-up completed ✅")
