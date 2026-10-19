-- Types match CLEAN_RATINGS_SCHEMA in transform.py. last_rated is stored as
-- a UTC timestamp.

CREATE EXTERNAL TABLE IF NOT EXISTS movie_clean.ratings (
  movie_id int,
  last_rated timestamp,
  avg_rating double,
  total_ratings int,
  std_dev double
)
STORED AS PARQUET
LOCATION 's3://ron-movie-lake-capstone/lake/clean/ratings/';
