-- Final, wide, analytics-ready table. This is what Power BI reads.
-- All the business logic (reach counts) lives in int_movies_joined.sql --
-- this stays a plain final `select *` per docs/DATA_MODEL.md section 2.

select * from {{ ref('int_movies_joined') }}
