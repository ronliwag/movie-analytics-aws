-- Types match CLEAN_EXTENDED_SCHEMA in transform.py. The list columns
-- (genres, cast, ...) are comma-joined strings; split them in queries.
--
-- `cast` is a reserved word, so it needs backticks here in DDL and double
-- quotes in queries: SELECT "cast" FROM movie_clean.movie_extended.

CREATE EXTERNAL TABLE IF NOT EXISTS movie_clean.movie_extended (
  id int,
  genres string,
  production_companies string,
  original_title string,
  original_language string,
  director string,
  `cast` string,
  production_country_codes string,
  production_country_names string,
  spoken_language_codes string,
  spoken_language_names string
)
STORED AS PARQUET
LOCATION 's3://ron-movie-lake-capstone/lake/clean/movie_extended/';
