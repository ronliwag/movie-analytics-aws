-- Bridge, grain: one row per (movie_id, iso_3166_1_code). Reach signal --
-- production countries, a secondary origin view (see docs/DATA_MODEL.md).

select distinct
    movie_id,
    country_code as iso_3166_1_code
from {{ ref('int_movie_countries') }}
