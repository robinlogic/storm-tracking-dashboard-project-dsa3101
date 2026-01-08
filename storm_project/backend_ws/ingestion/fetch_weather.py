# backend_ws/ingestion/fetch_weather.py

import requests
import pandas as pd
import posixpath
from datetime import datetime, timedelta
from backend_ws.secrets.db import get_conn
from backend_ws.app.gcs import upload_to_gcs
from backend_ws.app.config import WEATHER_OUTPUT, WEATHER_ENDPOINTS


def fetch_weather_for_timestamps(timestamps):
    """
    Fetch weather datasets only for timestamps where storms are detected.
    """
    if not timestamps:
        print("[ ] No storm timestamps found. Skipping weather fetch.")
        return

    for ts in timestamps:
        # Round to nearest 5 or 10 min if needed (API data is hourly or 5-min)
        start = (ts - timedelta(minutes=5)).isoformat() + "Z"
        end = (ts + timedelta(minutes=5)).isoformat() + "Z"

        for dataset, url in WEATHER_ENDPOINTS.items():
            try:
                print(f"[INFO] Fetching {dataset} for {ts}")
                resp = requests.get(url, params={"start": start, "end": end})
                resp.raise_for_status()
                data = resp.json()

                records = []
                for item in data.get("items", []):
                    timestamp = item.get("timestamp")
                    for reading in item.get("readings", []):
                        records.append({
                            "timestamp": timestamp,
                            "station_id": reading.get("station_id"),
                            "value": reading.get("value")
                        })

                if not records:
                    continue

                df = pd.DataFrame(records)
                df_csv = df.to_csv(index=False)

                folder = posixpath.join(WEATHER_OUTPUT, dataset)
                fname = f"{dataset}_{ts.strftime('%Y%m%d_%H%M')}.csv"
                gcs_path = posixpath.join(folder, fname)
                upload_to_gcs(df_csv, gcs_path)
                print(f"[✓] Saved {dataset} for {ts} → {gcs_path}")

                conn = get_conn()
                cur = conn.cursor()
                for _, row in df.iterrows():
                    cur.execute("""
                        INSERT IGNORE INTO weather_data (dataset, timestamp, station_id, value)
                        VALUES (%s, %s, %s, %s)
                    """, (dataset, row["timestamp"], row["station_id"], row["value"]))
                conn.commit()
                cur.close()
                conn.close()

            except Exception as e:
                print(f"[!] Failed fetching {dataset} for {ts}: {e}")