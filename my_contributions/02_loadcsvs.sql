USE storm_features; 


/*LOAD DATA INFILE '/var/lib/mysql-files/storm_features_with_centroids.csv'
INTO TABLE storm_profile_table
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(storm_id, datetime, storm_area_km2, @dummy, storm_centroid_lat, storm_centroid_long);*/


LOAD DATA INFILE '/var/lib/mysql-files/storm_profiles_2025-08-01_to_2025-10-31.csv'
INTO TABLE storm_profile_table_fe
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@datetime, @outlier, @storm_area, @centroid_x, @centroid_y, @storm_id)
SET
  datetime = @datetime,
  outlier = CASE
               WHEN @outlier IN ('True', 'true', '1') THEN 1
               ELSE 0
            END,
  storm_area_km2 = @storm_area,
  storm_centroid_long = @centroid_x,
  storm_centroid_lat = @centroid_y,
  storm_id = @storm_id;


LOAD DATA INFILE '/var/lib/mysql-files/storm_map_showcase.csv'
INTO TABLE storm_profile_table_fe
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(storm_id, datetime, storm_centroid_lat, storm_centroid_long, storm_area_km2);


LOAD DATA INFILE '/var/lib/mysql-files/aggregated_all_2025-08-01_to_2025-10-31.csv'
INTO TABLE agg_features_all_fe
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@average_storm_area, @average_storm_distance, @average_storm_duration, @interval_start)
SET
  average_storm_area_km2 = @average_storm_area,
  storm_distance_km = @average_storm_distance,
  storm_duration_min = @average_storm_duration,
  date = @interval_start;



LOAD DATA INFILE '/var/lib/mysql-files/aggregated_no_outliers_2025-08-01_to_2025-10-31.csv'
INTO TABLE agg_features_no_outliers_fe
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@average_storm_area, @average_storm_distance, @average_storm_duration, @interval_start)
SET
  average_storm_area_km2 = @average_storm_area,
  storm_distance_km = @average_storm_distance,
  storm_duration_min = @average_storm_duration,
  date = @interval_start;


LOAD DATA INFILE '/var/lib/mysql-files/rainy_days.csv'
INTO TABLE rainy_days
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@csv_date, number_of_rainy_days)
SET date = STR_TO_DATE(CONCAT(@csv_date, '-01'), '%Y-%m-%d');


LOAD DATA INFILE '/var/lib/mysql-files/radar_image_paths.csv'
INTO TABLE radar_images_fe
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(datetime, image_path);


LOAD DATA INFILE '/var/lib/mysql-files/air_temperature_1100_1600.csv'
INTO TABLE air_temperature
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(station_id, station_name, lat, lon, @datetime, temperature)
SET datetime = STR_TO_DATE(SUBSTRING_INDEX(@datetime,'+',1),'%Y-%m-%dT%H:%i:%s');

LOAD DATA INFILE '/var/lib/mysql-files/relative_humidity_1100_1600.csv'
INTO TABLE relative_humidity
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(station_id, station_name, lat, lon, @datetime, relative_humidity)
SET datetime = STR_TO_DATE(SUBSTRING_INDEX(@datetime,'+',1),'%Y-%m-%dT%H:%i:%s');

LOAD DATA INFILE '/var/lib/mysql-files/wind_speed_1100_1600.csv'
INTO TABLE wind_speed
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(station_id, station_name, lat, lon, @datetime, wind_speed)
SET datetime = STR_TO_DATE(SUBSTRING_INDEX(@datetime,'+',1),'%Y-%m-%dT%H:%i:%s');

LOAD DATA INFILE '/var/lib/mysql-files/wind_direction_1100_1600.csv'
INTO TABLE wind_direction
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(station_id, station_name, lat, lon, @datetime, wind_direction)
SET datetime = STR_TO_DATE(SUBSTRING_INDEX(@datetime,'+',1),'%Y-%m-%dT%H:%i:%s');
