-- Glue Data Catalog database for the clean lake tables (Phase 3).
-- A Glue "database" is only a namespace for table definitions; the data
-- itself stays in S3. The movie-pipeline IAM policy allows Glue databases
-- named movie_*.
--
-- Run in Athena with the movie-analytics workgroup. One statement per file:
-- Athena runs a single statement per query.

CREATE DATABASE IF NOT EXISTS movie_clean
COMMENT 'Clean tables written by scripts/pyspark/transform.py --target lake';
