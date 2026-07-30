-- TODO: unnest the multi-valued genre/production-company/country columns
-- into a tidy one-row-per-(movie_id, genre) shape (or split into separate
-- staging models per entity — your call, document the choice).

with source as (

    select * from {{ source('movie_analytics_raw', 'movie_extended') }}

)

select *
from source
