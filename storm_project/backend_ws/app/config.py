BUCKET_NAME = "backend_ws2"

# for fetching radar images
RADAR_OUTPUT = f"bronze/radar/"
RANGE_KM_VALUES = ["70km"]
BASE_URLS = {
    "70km": "https://www.nea.gov.sg/docs/default-source/rain-area/"
    }

# for fetching weather data
WEATHER_OUTPUT = f"bronze/weather/"
WEATHER_ENDPOINTS = {
    "air_temp": "https://api.data.gov.sg/v1/environment/air-temperature",
    "rainfall": "https://api.data.gov.sg/v1/environment/rainfall",
    "relative_humidity": "https://api.data.gov.sg/v1/environment/relative-humidity",
    "wind_speed": "https://api.data.gov.sg/v1/environment/wind-speed",
    "wind_direction": "https://api.data.gov.sg/v1/environment/wind-direction",
}

# for TITAN storm detection
DETECTION_INPUT = f"bronze/radar"         
DETECTION_OUTPUT = f"silver/storm_cells"

# for TITAN storm tracking
TRACKING_INPUT = f"silver/storm_cells"      
TRACKING_OUTPUT = f"silver/tracked_storms" 

# for storm profile aggregation
PROFILES_INPUT = f"silver/tracked_storms"
PROFILES_OUTPUT = f"gold/storm_profiles"



