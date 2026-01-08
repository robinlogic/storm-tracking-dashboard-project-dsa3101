# backend_ws/algorithm/titan.py

import io
import posixpath
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from backend_ws.app.gcs import upload_to_gcs, list_gcs_files, load_from_gcs
from backend_ws.app.config import DETECTION_INPUT, DETECTION_OUTPUT, RANGE_KM_VALUES

# --------------------------
# Helper: Read image from GCS
# --------------------------
def read_bgr_from_gcs(gcs_path):
    img_bytes = load_from_gcs(gcs_path)
    if img_bytes is None:
        return None
    img_array = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

# --------------------------
# Helper: Convert pixels → km²
# --------------------------
def pixels_to_km2(area_sqpixels, radar_range_km=70, img_width_px=217, img_height_px=120):
    """Approximate storm area in km² from pixel area."""
    km_per_pixel_x = (2 * radar_range_km) / img_width_px
    km_per_pixel_y = (2 * radar_range_km) / img_height_px
    return area_sqpixels * km_per_pixel_x * km_per_pixel_y

# --------------------------
# TITAN Storm Cell Detection
# --------------------------
def detect_storm_cells(image_path: str,
                       timestamp: str,
                       radar_range_km: str,
                       sat_min: int = 60,
                       val_min: int = 60,
                       perc_low: int = 12,
                       perc_high: int = 82,
                       exclude_cyan_lo: int = 90,
                       exclude_cyan_hi: int = 125,
                       min_area: int = 1,
                       morph_kernel: int = 0):
    """Detect storm cells using heavy rainfall colours (reds + purples)."""

    bgr = read_bgr_from_gcs(image_path)
    if bgr is None:
        raise FileNotFoundError(image_path)

    radar_hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # Filter valid pixels
    H, S, V = cv2.split(radar_hsv)
    valid = (S >= sat_min) & (V >= val_min)
    valid_hues = H[valid].astype(np.int32)
    if valid_hues.size == 0:
        return []

    # Percentile thresholds
    low_red_max = int(np.percentile(valid_hues, perc_low))
    purple_min  = int(np.percentile(valid_hues, perc_high))
    low_red_max = max(5, min(low_red_max, 25))
    purple_min  = max(low_red_max + 10, min(purple_min, 170))

    lower_red   = np.array([0, sat_min, val_min], dtype=np.uint8)
    upper_red   = np.array([low_red_max, 255, 255], dtype=np.uint8)
    lower_purp  = np.array([purple_min, sat_min, val_min], dtype=np.uint8)
    upper_purp  = np.array([179, 255, 255], dtype=np.uint8)

    mask_red = cv2.inRange(radar_hsv, lower_red, upper_red)
    mask_purp = cv2.inRange(radar_hsv, lower_purp, upper_purp)
    heavy_mask = cv2.bitwise_or(mask_red, mask_purp)

    # Exclude cyan
    lower_cyan = np.array([exclude_cyan_lo, 0, 0], dtype=np.uint8)
    upper_cyan = np.array([exclude_cyan_hi, 255, 255], dtype=np.uint8)
    cyan_mask = cv2.inRange(radar_hsv, lower_cyan, upper_cyan)
    heavy_mask[cyan_mask > 0] = 0

    # Optional morphology
    if morph_kernel > 0:
        k = np.ones((morph_kernel, morph_kernel), np.uint8)
        heavy_mask = cv2.morphologyEx(heavy_mask, cv2.MORPH_OPEN, k)
        heavy_mask = cv2.morphologyEx(heavy_mask, cv2.MORPH_DILATE, k)

    heavy_mask[heavy_mask > 0] = 255
    contours, _ = cv2.findContours(heavy_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cells = []
    radar_range_km = float(radar_range_km)
    img_h, img_w = bgr.shape[:2]

    for cnt in contours:
        area_px = cv2.contourArea(cnt)
        if area_px < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        x_center, y_center = x + w / 2, y + h / 2

        # Compute approximate storm area in km²
        storm_area_km2 = pixels_to_km2(area_px, radar_range_km, img_w, img_h)

        cells.append({
            "timestamp": timestamp,
            "radar_range_km": radar_range_km,
            "x_pixels": int(x_center),
            "y_pixels": int(y_center),
            "width_pixels": int(w),
            "height_pixels": int(h),
            "area_sqpixels": int(area_px),
            "storm_area_km2": storm_area_km2
        })

    return cells

# --------------------------
# Process Radar for TITAN
# --------------------------
def process_radar_for_titan(date_str):
    """Process radar images for a given date and upload storm cells to GCS."""

    print(f"[TITAN] Processing radar images for {date_str}")
    radar_root = DETECTION_INPUT
    radar_ranges = RANGE_KM_VALUES

    for radar_range in radar_ranges:
        folder = posixpath.join(radar_root, radar_range, date_str.replace("-", ""))
        image_files = list_gcs_files(folder)

        for img_path in image_files:
            if not img_path.endswith(".png"):
                continue

            # Extract timestamp
            fname = posixpath.basename(img_path).replace(".png", "")
            parts = fname.split("_")
            if len(parts) < 3:
                print(f"[!] Skipping {img_path}, unexpected filename format")
                continue
            time_str = parts[-1]
            try:
                ts = datetime.strptime(date_str + time_str, "%Y-%m-%d%H%M")
            except ValueError:
                print(f"[!] Skipping {img_path}, invalid timestamp: {time_str}")
                continue

            cells = detect_storm_cells(
                image_path=img_path,
                timestamp=ts.strftime("%Y-%m-%d %H:%M"),
                radar_range_km=radar_range.replace("km", "")
            )

            if cells:
                gcs_path = posixpath.join(
                    DETECTION_OUTPUT,
                    f"storm_cells_{radar_range}_{ts.strftime('%Y%m%d_%H%M')}.csv"
                )
                df_csv = pd.DataFrame(cells).to_csv(index=False)
                upload_to_gcs(df_csv, gcs_path)
                print(f"[TITAN] Uploaded {len(cells)} storm cells to {gcs_path}")
            else:
                print(f"[TITAN] No storm cells detected in {img_path}")
