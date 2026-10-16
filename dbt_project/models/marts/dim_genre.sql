-- Deduped genre catalog. genre_id is a surrogate key hashed from the
-- normalized name -- movie_genre.sql computes the same hash independently,
-- so no join is needed to resolve the FK.

with genre_names as (

    select distinct genre_name from {{ ref('int_movie_genres') }}

),

keyed as (

    select
        {{ dbt_utils.generate_surrogate_key(['lower(genre_name)']) }} as genre_id,
        genre_name
    from genre_names

)

select
    genre_id,
    min(genre_name) as name
from keyed
group by genre_id
