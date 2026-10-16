-- Bridge, grain: one row per (movie_id, iso_639_1_code). Reach signal --
-- spoken languages. The movie's single original_language_code is a direct
-- attribute on the fact/mart (Task 4), not represented here.

select distinct
    movie_id,
    language_code as iso_639_1_code
from {{ ref('int_movie_languages') }}
