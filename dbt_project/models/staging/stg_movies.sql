
with source as (

    select * from {{ source('movie_analytics_raw', 'movies_main') }}

)

select
    id::integer as movie_id,
    title,
    release_date::date as release_date
from source
