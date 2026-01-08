from storm_database import StormDatabase  # or copy class here

db_url = "mysql+mysqlconnector://root:dsa3101@localhost:5002/storm_features"
storm_db = StormDatabase(db_url)

# Load data
storm_db.load_storm_profiles("2025-07-01", "2025-07-10")

# Inspect queried dataframe
print(storm_db.get_queried_df().head())
print(storm_db.get_queried_df().columns)

# Aggregated storm area
print(storm_db.get_aggregated_area(interval='D').head())
print(storm_db.get_aggregated_area(interval='D').columns)

# Aggregated distance/duration
print(storm_db.get_aggregated_distance_duration(interval='D').head())
print(storm_db.get_aggregated_distance_duration(interval='D').columns)

# Rainy days
print(storm_db.get_rainy_days().head())
print(storm_db.get_rainy_days().columns)

# Radar images
#print(storm_db.get_radar_images())
