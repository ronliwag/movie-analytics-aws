-- Bridge, grain: one row per (movie_id, person_id). person_id is hashed
-- the same way as dim_person.sql computes it -- no join needed to resolve
-- it.

select distinct
    movie_id,
    {{ dbt_utils.generate_surrogate_key(['lower(person_name)']) }} as person_id
from {{ ref('int_movie_directors') }}
