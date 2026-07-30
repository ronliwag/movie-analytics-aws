-- Light renaming/casting only. No joins or business logic here.

with source as (

    select * from {{ source('movie_analytics_raw', 'movies_main') }}

)

select
    -- TODO: rename/cast raw columns, e.g.
    -- movie_id as movie_id,
    -- title as title,
    -- release_date as release_date,
    -- budget as budget,
    -- revenue as revenue
    *
from source
