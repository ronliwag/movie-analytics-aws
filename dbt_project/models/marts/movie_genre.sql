-- Bridge, grain: one row per (movie_id, genre_id). genre_id is hashed the
-- same way as dim_genre.sql computes it -- no join needed to resolve it.

select distinct
    movie_id,
    {{ dbt_utils.generate_surrogate_key(['lower(genre_name)']) }} as genre_id
from {{ ref('int_movie_genres') }}
