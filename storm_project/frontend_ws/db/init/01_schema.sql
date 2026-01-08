USE storm_features;

DROP TABLE IF EXISTS storm_profile_table_be;
CREATE TABLE storm_profile_table_be (
    storm_id VARCHAR(15),
    datetime DATETIME NOT NULL,
    storm_area_km2 FLOAT,
    storm_centroid_lat FLOAT,
    storm_centroid_long FLOAT,
    outlier BOOLEAN default FALSE
);

DROP TABLE IF EXISTS storm_profile_table_fe;
CREATE TABLE storm_profile_table_fe (
    storm_id VARCHAR(15),
    datetime DATETIME NOT NULL,
    storm_area_km2 FLOAT,
    storm_centroid_lat FLOAT,
    storm_centroid_long FLOAT,
    outlier BOOLEAN default FALSE
);

DROP TABLE IF EXISTS agg_features_no_outliers_be;
CREATE TABLE agg_features_no_outliers_be (
    date DATE,
    average_storm_area_km2 FLOAT,
    storm_distance_km FLOAT,
    storm_duration_min FLOAT
    );

DROP TABLE IF EXISTS agg_features_no_outliers_fe;
CREATE TABLE agg_features_no_outliers_fe (
    date DATE,
    average_storm_area_km2 FLOAT,
    storm_distance_km FLOAT,
    storm_duration_min FLOAT
    );

DROP TABLE IF EXISTS agg_features_all_be;
CREATE TABLE agg_features_all_be (
    date DATE,
    average_storm_area_km2 FLOAT,
    storm_distance_km FLOAT,
    storm_duration_min FLOAT
    );

DROP TABLE IF EXISTS agg_features_all_fe;
CREATE TABLE agg_features_all_fe (
    date DATE,
    average_storm_area_km2 FLOAT,
    storm_distance_km FLOAT,
    storm_duration_min FLOAT
    );

DROP TABLE IF EXISTS rainy_days;
CREATE TABLE rainy_days (
    date DATE PRIMARY KEY,
    number_of_rainy_days INT
);

DROP TABLE IF EXISTS radar_images_fe;
CREATE TABLE radar_images_fe (
    datetime DATETIME PRIMARY KEY,
    image_path VARCHAR(255)
);

DROP TABLE IF EXISTS radar_images_be;
CREATE TABLE radar_images_be (
    datetime DATETIME PRIMARY KEY,
    image_path VARCHAR(255)
);

DROP TABLE IF EXISTS air_temperature;
CREATE TABLE air_temperature (
    station_id VARCHAR(4),
    station_name VARCHAR(30),
    lat FLOAT,
    lon FLOAT,
    datetime DATETIME,
    temperature FLOAT
);

DROP TABLE IF EXISTS relative_humidity;
CREATE TABLE relative_humidity (
    station_id VARCHAR(4),
    station_name VARCHAR(30),
    lat FLOAT,
    lon FLOAT,
    datetime DATETIME,
    relative_humidity FLOAT
);

DROP TABLE IF EXISTS wind_speed;
CREATE TABLE wind_speed (
    station_id VARCHAR(4),
    station_name VARCHAR(30),
    lat FLOAT,
    lon FLOAT,
    datetime DATETIME,
    wind_speed FLOAT
);

DROP TABLE IF EXISTS wind_direction;
CREATE TABLE wind_direction (
    station_id VARCHAR(4),
    station_name VARCHAR(30),
    lat FLOAT,
    lon FLOAT,
    datetime DATETIME,
    wind_direction FLOAT
);
