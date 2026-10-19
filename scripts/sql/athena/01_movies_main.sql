-- EXTERNAL: Athena only stores this definition in the Glue Catalog. Dropping
-- the table never deletes the Parquet files under LOCATION.
--
-- Column types must match the Parquet files that transform.py writes with
-- CLEAN_MOVIES_SCHEMA (e.g. int, not bigint), or queries fail with
-- HIVE_BAD_DATA. LOCATION uses s3://, not Spark's s3a://.

CREATE EXTERNAL TABLE IF NOT EXISTS movie_clean.movies_main (
  id int,
  title string,
  release_date date,
  budget double,
  revenue double
)
STORED AS PARQUET
LOCATION 's3://ron-movie-lake-capstone/lake/clean/movies_main/';
