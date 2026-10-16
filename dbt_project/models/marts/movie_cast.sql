-- Bridge, grain: one row per (movie_id, person_id). person_id is hashed
-- the same way as dim_person.sql computes it -- no join needed to resolve
-- it. billing_order is TMDB's cast `order` field (see int_movie_cast.sql)
-- -- min() keeps the most prominent billing if the same name appears
-- twice in one movie's raw cast list.

select
    movie_id,
    {{ dbt_utils.generate_surrogate_key(['lower(person_name)']) }} as person_id,
    min(billing_order) as billing_order
from {{ ref('int_movie_cast') }}
group by movie_id, {{ dbt_utils.generate_surrogate_key(['lower(person_name)']) }}
