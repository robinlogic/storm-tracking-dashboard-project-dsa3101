from sqlalchemy import create_engine, text
from mahalanobis import mahalanobis
import pandas as pd
import numpy as np
import requests

class StormDatabase:
    """
    A SQLAlchemy-based data manager for storm feature analytics.

    The StormDatabase class handles data retrieval, aggregation, and 
    synchronization between the frontend MySQL database and backend API.
    It provides methods to query storm profiles, radar images, and 
    environmental metrics, with automatic fallbacks between backend (_be) 
    and frontend (_fe) tables when data is unavailable.

    Features:
    - Connects to the MySQL storm_features database via SQLAlchemy.
    - Retrieves aggregated metrics (area, distance, duration) and radar imagery.
    - Integrates outlier detection using Mahalanobis distance.
    - Supports API-based population of frontend tables from backend services.
    - Provides date-range filtering and data cleaning options for dashboard visualization.
    """
    
    allowed_intervals = ('Y', 'M', 'D', '15min')
    DB_URL = "mysql+pymysql://root:dsa3101@mysql:3306/storm_features"
    BACKEND_URL = "http://backend:8000/api/titan"  # Docker service name
    #BACKEND_URL = "http://host.docker.internal:8080/api/titan" # testing
    AREA = "storm_area"
    DIST_DUR = "storm_distance_duration"
    RADAR_PATHS_PROFILES = "radar_images_storm_profiles#APPENDBREAK"
    RADAR_IMAGE = "radar_image" # SINGLE RADAR IMAGE QUERY
    INTERVAL = "D" # RESTRICT TO DAY ONLY
    
    def __init__(self):
        self.engine = create_engine(self.DB_URL)

    # Generic helper
    def _is_table_empty(self, table):
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            return result.scalar() == 0


    # --- Loaders ---
    def get_storm_profiles(self, start_date, end_date):
        """
        Query BE if filled, else FE.

        Using FE by default for storm dynamics.
        """

        # TRY FALLBACK ON FE DB
        if start_date == "17-10-2025 11:00" and end_date == "17-10-2025 16:00":
            print("[StormDatabase] Using FE table for storm dynamics showcase...")
            query = f"SELECT * FROM storm_profile_table_fe WHERE datetime BETWEEN :start AND :end"
            df = pd.read_sql(text(query), self.engine, params={"start": start_date, "end": end_date})
            
            df['outlier'] = df['outlier'].astype(bool)
            return df
        
        table = "storm_profile_table_be" if not self._is_table_empty("storm_profile_table_be") else "storm_profile_table_fe"
        query = f"SELECT * FROM {table} WHERE datetime BETWEEN :start AND :end"
        df = pd.read_sql(text(query), self.engine, params={"start": start_date, "end": end_date})

        # TRY FALLBACK ON FE DB
        if df.empty:
            print(f"[StormDatabase] BE no results, Trying FE table... start: {start_date}, end: {end_date}")
            query = f"SELECT * FROM storm_profile_table_fe WHERE datetime BETWEEN :start AND :end"
            df = pd.read_sql(text(query), self.engine, params={"start": start_date, "end": end_date})
            
        df['outlier'] = df['outlier'].astype(bool)
        return df

    def get_radar_images(self, start_date, end_date):
        """Always from FE table"""
        table = "radar_images_fe"
        query = f"SELECT * FROM {table} WHERE datetime BETWEEN :start AND :end"
        df = pd.read_sql(text(query), self.engine, params={"start": start_date, "end": end_date})
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df.sort_values("datetime")

        
    def get_aggregated_area(self, clean=True, start_date=None, end_date=None):
        """Return clean/raw BE or FE aggregated area tables within date range"""
        
        # Choose table (preferring BE if populated)
        table = (
            "agg_features_no_outliers_be" if clean else "agg_features_all_be"
        ) if not self._is_table_empty("agg_features_no_outliers_be") else (
            "agg_features_no_outliers_fe" if clean else "agg_features_all_fe"
        )
    
        # Build base query
        query = f"SELECT average_storm_area_km2, date FROM {table}"
    
        # Add WHERE clause only if both dates provided
        params = {}
        if start_date and end_date:
            query += " WHERE date BETWEEN :start AND :end"
            params = {"start": start_date, "end": end_date}
    
        # Execute query
        df = pd.read_sql(text(query), self.engine, params=params)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values("date")

    def get_aggregated_distance(self, clean=True, start_date=None, end_date=None):
        """Return clean/raw BE or FE aggregated area tables within date range"""
        
        # Choose table (preferring BE if populated)
        table = (
            "agg_features_no_outliers_be" if clean else "agg_features_all_be"
        ) if not self._is_table_empty("agg_features_no_outliers_be") else (
            "agg_features_no_outliers_fe" if clean else "agg_features_all_fe"
        )
    
        # Build base query
        query = f"SELECT storm_distance_km, date FROM {table}"
    
        # Add WHERE clause only if both dates provided
        params = {}
        if start_date and end_date:
            query += " WHERE date BETWEEN :start AND :end"
            params = {"start": start_date, "end": end_date}
    
        # Execute query
        df = pd.read_sql(text(query), self.engine, params=params)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values("date")

    def get_aggregated_duration(self, clean=True, start_date=None, end_date=None):
        """Return clean/raw BE or FE aggregated area tables within date range"""
        
        # Choose table (preferring BE if populated)
        table = (
            "agg_features_no_outliers_be" if clean else "agg_features_all_be"
        ) if not self._is_table_empty("agg_features_no_outliers_be") else (
            "agg_features_no_outliers_fe" if clean else "agg_features_all_fe"
        )
    
        # Build base query
        query = f"SELECT storm_duration_min, date FROM {table}"

    
        # Add WHERE clause only if both dates provided
        params = {}
        if start_date and end_date:
            query += " WHERE date BETWEEN :start AND :end"
            params = {"start": start_date, "end": end_date}
    
        # Execute query
        df = pd.read_sql(text(query), self.engine, params=params)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values("date")




    def get_rainy_days(self, start_date, end_date):
        """Always from FE table"""
        #start_month = pd.to_datetime(start_date).strftime("%Y-%m")
        #end_month = pd.to_datetime(end_date).strftime("%Y-%m")
        query = """
            SELECT * FROM rainy_days
            WHERE DATE_FORMAT(date, '%Y-%m') BETWEEN DATE_FORMAT(:start, '%Y-%m') AND DATE_FORMAT(:end, '%Y-%m')
        """
        df = pd.read_sql(text(query), self.engine, params={"start": start_date, "end": end_date})
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values("date")

    def get_other_storm_features(self, start_date, end_date):
        """Combine raw sensor tables: temp, RH, wind speed, direction."""
        # Each FE table exists permanently
        tables = ["air_temperature", "relative_humidity", "wind_speed", "wind_direction"]
        dfs = {}
        for t in tables:
            q = text(f"SELECT * FROM {t} WHERE datetime BETWEEN :start AND :end")
            dfs[t] = pd.read_sql(q, self.engine, params={"start": start_date, "end": end_date})


        wind_df = pd.merge(
            dfs["wind_speed"],
            dfs["wind_direction"],
            on=["station_id", "station_name", "datetime", "lat", "lon"],
            how="outer"  # or 'inner' if both always match
        ).sort_values(["station_id", "datetime"])

        temprh_df = pd.merge(
            dfs["air_temperature"],
            dfs["relative_humidity"],
            on=["station_id", "station_name", "datetime", "lat", "lon"],
            how="outer"  # or 'inner' if both always match
        ).sort_values(["station_id", "datetime"])


        merged_df = (
            temprh_df
            .merge(wind_df, on=["station_id","station_name", "datetime", "lat", "lon"], how="outer")
        )
        
        return merged_df

    def _try_backend(self, endpoint, params):
        try:
            url = f"{self.BACKEND_URL}/{endpoint}"
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and len(data) > 0:
                    print(f"✅ {endpoint} loaded successfully.")
                    return data
            print(f"⚠️ {endpoint} returned empty or invalid response.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[StormDatabase] Backend unreachable for {endpoint}: {e}")
            return None

    def populateDB(self, start_date, end_date):
        params = {"start_date": start_date, "end_date": end_date}

        i = 0

        # 1️⃣ --- Storm Profiles + Radar Paths ---
        data = self._try_backend(self.RADAR_PATHS_PROFILES, params)

        # Extract radar image paths if available
        if data and "radar_images" in data:
            paths, datetimes = [], []
            pattern = re.compile(r"radar_\d+km_(\d{8})_(\d{4})\.png")

            for url in data["radar_images"]:
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                gcs_path = qs.get("gcs_path", [None])[0]
                if not gcs_path:
                    continue

                match = pattern.search(gcs_path)
                if not match:
                    continue
                date_str, time_str = match.groups()
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M")

            radar_df = pd.DataFrame({"datetime": datetimes, "image_path": paths}).sort_values("datetime")
            radar_df.to_sql("radar_images_be", self.engine, if_exists="append", index=False)
            i +=1
            print(f"✅ Inserted {len(radar_df)} radar image paths into radar_images_be")

        # 2️⃣ --- Aggregated Storm Metrics ---
        distdur_data = self._try_backend(self.DIST_DUR, params)
        if distdur_data:
            for key in ["aggregated_all", "aggregated_no_outliers"]:
                if key in distdur_data:
                    df = pd.DataFrame(distdur_data[key])
                    df.rename(columns={
                        "date": "date",
                        "avg_area": "average_storm_area_km2",
                        "total_distance_km": "storm_distance_km",
                        "duration_min": "storm_duration_min"
                    }, inplace=True)
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                    table_name = f"agg_features_{'all' if 'all' in key else 'no_outliers'}_be"
                    col_order = [
                        "date",
                        "average_storm_area_km2",
                        "storm_distance_km",
                        "storm_duration_min"
                    ]
                    df = df[col_order]
                    df.to_sql(table_name, self.engine, if_exists="append", index=False)
                    print(f"✅ Inserted {len(df)} rows into {table_name}")
                    i+=1
                    
            if distdur_data and "storm_profiles" in distdur_data:
                df = pd.DataFrame(distdur_data["storm_profiles"])
                if not df.empty:
                    # Convert datetime
                    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
                    df["datetime"] = df["datetime"].dt.tz_convert("Asia/Singapore").dt.tz_localize(None)
                    df.rename(columns={
                        "storm_area": "storm_area_km2",
                        "storm_centroid_x": "storm_centroid_long",
                        "storm_centroid_y": "storm_centroid_lat",
                    }, inplace=True)
                    col_order = [
                        "storm_id",
                        "datetime",
                        "storm_area_km2",
                        "storm_centroid_lat",
                        "storm_centroid_long",
                        "outlier"
                    ]
                    df = df[col_order]
                    # Save to MySQL
                    df.to_sql("storm_profile_table_be", self.engine, if_exists="replace", index=False)
                    print(f"✅ Inserted {len(df)} storm profiles into storm_profile_table_be")
                    i+=1

        print("🎯 Database population completed successfully.") if i==3 else print("❌ Database not populated, using Frontend data cache.")
