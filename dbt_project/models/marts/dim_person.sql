-- Deduped person catalog, shared by movie_director and movie_cast.
-- person_id is a surrogate key hashed from the normalized name -- both
-- bridge models compute the same hash independently, so no join is needed
-- to resolve the FK.
--
-- Known limitation (see docs/DATA_MODEL.md): person is name-based, not
-- TMDB-id-based, so two different real people sharing a name incorrectly
-- collapse into one row here.

with names as (

    select person_name from {{ ref('int_movie_directors') }}
    union
    select person_name from {{ ref('int_movie_cast') }}

),

keyed as (

    select
        {{ dbt_utils.generate_surrogate_key(['lower(person_name)']) }} as person_id,
        person_name
    from names

)

select
    person_id,
    min(person_name) as name
from keyed
group by person_id
