# backend_ws/ingestion/fetch_radar.py
import posixpath
import requests
from datetime import datetime, timedelta, timezone
from backend_ws.secrets.db import get_conn
from backend_ws.algorithm.titan import process_radar_for_titan
from backend_ws.app.gcs import upload_to_gcs
from backend_ws.app.config import BUCKET_NAME, RADAR_OUTPUT, RANGE_KM_VALUES, BASE_URLS
from backend_ws.ingestion.fetch_weather import fetch_weather_for_timestamps

SINGAPORE_TZ = timezone(timedelta(hours=8))


# --------------------------
# Generate NEA radar URL
# --------------------------
def generate_url(timestamp: datetime, range_km: str) -> str:
    ts_str = timestamp.strftime("%Y%m%d%H%M")
    return f"{BASE_URLS[range_km]}dpsri_{range_km}_{ts_str}0000dBR.dpsri.png"


# --------------------------
# Fetch radar for a single timestamp
# --------------------------
def fetch_next_radar_for_timestamp(next_ts: datetime):
    """Fetch radar images for all ranges at a single timestamp."""
    new_images_downloaded = False
    storm_timestamps = []

    for rng in RANGE_KM_VALUES:
        url = generate_url(next_ts, rng)
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                gcs_folder = posixpath.join(RADAR_OUTPUT, rng, next_ts.strftime("%Y%m%d"))
                gcs_path = posixpath.join(gcs_folder, f"radar_{rng}_{next_ts.strftime('%Y%m%d_%H%M')}.png")
                upload_to_gcs(r.content, gcs_path, content_type="image/png")
                print(f"[INFO] Radar image uploaded: {gcs_path}")

                # Insert metadata to DB
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT IGNORE INTO radar_data (range_km, timestamp, file_url)
                        VALUES (%s, %s, %s)
                    """, (rng, next_ts, url))
                    conn.commit()
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"[!] Failed to insert radar metadata: {e}")

                new_images_downloaded = True
            else:
                print(f"[ ] Radar not available: {url}")
        except Exception as e:
            print(f"[!] Error fetching radar: {e}")

    return storm_timestamps


# --------------------------
# Fetch radar for a full day in 5-min intervals
# --------------------------
def fetch_radar_for_day(date_obj: datetime.date):
    """Fetch radar for all 5-min intervals of a specific date."""
    start_ts = datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=SINGAPORE_TZ)
    end_ts = start_ts + timedelta(days=1)
    current_ts = start_ts
    all_storm_timestamps = []

    while current_ts < end_ts:
        minute = (current_ts.minute // 5) * 5
        current_ts_rounded = current_ts.replace(minute=minute, second=0, microsecond=0)

        storm_ts = fetch_next_radar_for_timestamp(current_ts_rounded)
        if storm_ts:
            all_storm_timestamps.extend(storm_ts)

        current_ts += timedelta(minutes=5)

    return all_storm_timestamps
