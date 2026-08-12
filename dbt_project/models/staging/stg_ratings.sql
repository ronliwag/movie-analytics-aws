
with source as (

    select * from {{ source('movie_analytics_raw', 'ratings') }}

)

select
    movie_id::integer as movie_id,
    last_rated::timestamp as last_rated,
    avg_rating::double precision as avg_rating,
    total_ratings::integer as total_ratings,
    std_dev::double precision as std_dev
from source
