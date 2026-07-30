-- TODO: flatten the nested rating summaries from the source table into
-- one row per (movie_id, rating_source) — mirrors the Week 2 Rating class.

with source as (

    select * from {{ source('movie_analytics_raw', 'ratings') }}

)

select *
from source
