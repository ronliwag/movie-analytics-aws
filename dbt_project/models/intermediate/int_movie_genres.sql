with extended as (

    select movie_id, genres
    from {{ ref('stg_movie_extended') }}
    where genres is not null

)

select distinct
    movie_id,
    trim(genre_name) as genre_name
from extended,
    unnest(string_to_array(genres, ',')) as genre_name
where trim(genre_name) != ''
