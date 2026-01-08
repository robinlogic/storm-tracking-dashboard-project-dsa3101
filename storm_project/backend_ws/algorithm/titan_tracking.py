# backend_ws/algorithm/titan_tracking.py

import io
import posixpath
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import chi2
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter
# from sklearn.preprocessing import StandardScaler
from backend_ws.secrets.db import get_conn
from backend_ws.app.gcs import upload_to_gcs, load_from_gcs, list_gcs_files
from backend_ws.app.config import TRACKING_INPUT, TRACKING_OUTPUT, RANGE_KM_VALUES

MAX_MISSED = 2
MAX_DIST = 20.0  # maximum distance in Mahalanobis units to consider a match

# Distance Helper
class StormTrack:
    def __init__(self, storm_id, first_cell):
        self.storm_id = storm_id
        self.kf = self._init_kalman(first_cell)
        self.cells = [first_cell]
        self.last_seen = first_cell['timestamp']
        # Keep track of number of consecutive missed frames, optional
        self.missed = 0

    def _init_kalman(self, cell):
        kf = KalmanFilter(dim_x=6, dim_z=3) 
        dt = 5.0  # time interval in minutes
        kf.F = np.array([[1, 0, 0, dt, 0, 0],
                         [0, 1, 0, 0, dt, 0], 
                         [0, 0, 1, 0, 0, dt],
                         [0, 0, 0, 1, 0, 0],
                         [0, 0, 0, 0, 1, 0],
                         [0, 0, 0, 0, 0, 1]])
        kf.H = np.array([[1, 0, 0, 0, 0, 0],
                         [0, 1, 0, 0, 0, 0],
                         [0, 0, 1, 0, 0, 0]])
        kf.R *= 10.0
        kf.P *= 100.0
        kf.Q *= np.eye(6)* 0.01
        kf.x = np.array([[cell['x_pixels']],
                         [cell['y_pixels']],
                         [cell['area_sqpixels']],
                         [0], [0], [0]])
        return kf
    
    def predict(self):
        self.kf.predict()
        x, y, area = self.kf.x[0,0], self.kf.x[1,0], self.kf.x[2,0]
        return np.array([x, y, area])
    
    def update(self, cell):
        z = np.array([[cell['x_pixels']],
                      [cell['y_pixels']],
                      [cell['area_sqpixels']]])
        self.kf.update(z)
        self.cells.append(cell)
        self.last_seen = cell['timestamp']
        self.missed = 0

    def mark_missed(self):
        self.missed += 1
    
    def is_active(self, current_timestamp=None):
        """
        Returns True if the storm is still active. Checks both missed frames and actual timestamp gaps.
        """
        if current_timestamp is None:
            # Default behavior: same as before (frame-based)
            return self.missed <= MAX_MISSED
        else:
            # Time-based check: gap in minutes
            delta_minutes = (current_timestamp - self.last_seen).total_seconds() / 60.0
            return delta_minutes <= MAX_MISSED * 5  # MAX_MISSED frames * 5 minutes per frame
    
    def get_trajectory(self):
        return [(c['timestamp'], c['x_pixels'], c['y_pixels'], c['area_sqpixels']) for c in self.cells]



def compute_cov_inv(cells):
    # 3 features: x, y, area
    data = np.array([[c['x_pixels'], c['y_pixels'], c['area_sqpixels']] for c in cells])
    n_features = data.shape[1]

    if len(data) < 2:
        # Not enough points → small identity of correct size
        return np.linalg.inv(np.eye(n_features) * 1e-3)

    cov_matrix = np.cov(data, rowvar=False)

    # Handle NaNs or singular matrices
    if not np.isfinite(cov_matrix).all():
        cov_matrix = np.eye(n_features) * 1e-3

    try:
        cov_inv = np.linalg.inv(cov_matrix)
    except np.linalg.LinAlgError:
        cov_inv = np.linalg.inv(np.eye(n_features) * 1e-3)

    return cov_inv


def mahalanobis_distance(cell1, cell2, cov_inv, scaler):
    vec1 = np.array([cell1['x_pixels'], cell1['y_pixels'], cell1['area_sqpixels']])
    vec2 = np.array([cell2['x_pixels'], cell2['y_pixels'], cell2['area_sqpixels']])
    vecs_scaled = scaler.fit_transform(np.array([vec1, vec2]))
    delta = vecs_scaled[0] - vecs_scaled[1]
    return float(np.dot(np.dot(delta.T, cov_inv), delta))


# DB Insert Helper
def insert_tracked_storms_to_db(tracked_storms_csv: str):
    if not tracked_storms_csv.strip():
        return
    df = pd.read_csv(io.StringIO(tracked_storms_csv))
    if df.empty:
        return
    try:
        conn = get_conn()
        cur = conn.cursor()
        insert_query = """
            INSERT IGNORE INTO storm_tracks
            (storm_id, radar_range_km, timestamp, x_pixels, y_pixels, width_pixels, height_pixels, area_sqpixels, storm_area_km2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = [
            (
                row['storm_id'], row['radar_range_km'], row['timestamp'],
                row['x_pixels'], row['y_pixels'], row['width_pixels'], row['height_pixels'],
                row['area_sqpixels'], row['storm_area_km2']
            )
            for _, row in df.iterrows()
        ]
        cur.executemany(insert_query, data)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB] Failed to insert tracked storms: {e}")


# Main Tracking Function
def track_storms_for_date(date_str: str):
    print(f"[TITAN Tracking] Processing date: {date_str}")
    storm_tracks = []
    date_compact = date_str.replace("-", "")
    next_storm_id = 1

    for radar_range in RANGE_KM_VALUES:
        all_files = list_gcs_files(TRACKING_INPUT)
        csv_files = sorted([
            f for f in all_files
            if f.endswith(".csv") and radar_range in f and date_compact in f
        ])

        print(f"[TITAN Tracking] Found {len(csv_files)} files for {radar_range} on {date_str}")

        for csv_file in csv_files:
            csv_bytes = load_from_gcs(csv_file)
            if not csv_bytes:
                print(f"[!] Skipping {csv_file}, could not load from GCS")
                continue

            df = pd.read_csv(io.BytesIO(csv_bytes))
            if df.empty:
                print(f"[!] Skipping {csv_file}, empty DataFrame")
                continue

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            new_cells = df.to_dict(orient='records')

            # Only keep active tracks that haven't disappeared for too long
            active_tracks = [t for t in storm_tracks if t.is_active(current_timestamp=df['timestamp'].min())]

            # Predict positions of active tracks
            predictions = [t.predict() for t in active_tracks]

            # If no active tracks, create new ones
            if not active_tracks:
                for cell in new_cells:
                    unique_id = f"{next_storm_id}_{date_compact}"
                    storm_tracks.append(StormTrack(unique_id, cell))
                    next_storm_id += 1
                continue

            # Build cost matrix (Euclidean)
            cell_coords = np.array([[c['x_pixels'], c['y_pixels'], c['area_sqpixels']] for c in new_cells])
            cost_matrix = np.zeros((len(predictions), len(cell_coords)))
            for i, pred in enumerate(predictions):
                for j, cell in enumerate(cell_coords):
                    cost_matrix[i, j] = np.linalg.norm(pred - cell)

            # Hungarian assignment
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            assigned_tracks, assigned_cells = set(), set()
            for i, j in zip(row_ind, col_ind):
                if cost_matrix[i, j] < MAX_DIST:
                    active_tracks[i].update(new_cells[j])
                    assigned_tracks.add(i)
                    assigned_cells.add(j)

            # Create new tracks for unassigned cells
            for k, cell in enumerate(new_cells):
                if k not in assigned_cells:
                    unique_id = f"{next_storm_id}_{date_compact}"
                    storm_tracks.append(StormTrack(unique_id, cell))
                    next_storm_id += 1

            # Mark missed tracks
            for t_idx, track in enumerate(active_tracks):
                if t_idx not in assigned_tracks:
                    track.mark_missed()

    # Export to CSV and upload to GCS + DB
    rows = []
    for track in storm_tracks:
        for cell in track.cells:
            rows.append({
                'storm_id': track.storm_id,
                'timestamp': cell['timestamp'],
                'radar_range_km': cell['radar_range_km'],
                'x_pixels': cell['x_pixels'],
                'y_pixels': cell['y_pixels'],
                'width_pixels': cell['width_pixels'],
                'height_pixels': cell['height_pixels'],
                'area_sqpixels': cell['area_sqpixels'],
                'storm_area_km2': cell['storm_area_km2']
            })

    if rows:
        df_out = pd.DataFrame(rows)
        for radar_range in RANGE_KM_VALUES:
            range_rows = df_out[df_out['radar_range_km'] == float(radar_range.replace("km",""))]
            for ts, group in range_rows.groupby(pd.Grouper(key='timestamp', freq='5min')):
                if group.empty:
                    continue
                gcs_path = posixpath.join(
                    TRACKING_OUTPUT,
                    f"tracked_storms_{radar_range}_{ts.strftime('%Y%m%d_%H%M')}.csv"
                )
                csv_bytes = group.to_csv(index=False)
                upload_to_gcs(csv_bytes, gcs_path)
                insert_tracked_storms_to_db(csv_bytes)
                print(f"[TITAN Tracking] Uploaded {len(group)} cells to {gcs_path}")
    else:
        print(f"[TITAN Tracking] No storms detected for {date_str}")

    return {track.storm_id: track.get_trajectory() for track in storm_tracks}