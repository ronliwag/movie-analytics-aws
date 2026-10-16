-- Splits stg_movie_extended.production_companies (comma-packed) into one
-- row per (movie_id, company_name). Grain: movie x company.

with extended as (

    select movie_id, production_companies
    from {{ ref('stg_movie_extended') }}
    where production_companies is not null

)

select distinct
    movie_id,
    trim(company_name) as company_name
from extended,
    unnest(string_to_array(production_companies, ',')) as company_name
where trim(company_name) != ''
