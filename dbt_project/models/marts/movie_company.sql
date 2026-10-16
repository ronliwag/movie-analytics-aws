-- Bridge, grain: one row per (movie_id, production_company_id).
-- production_company_id is hashed the same way as
-- dim_production_company.sql computes it -- no join needed to resolve it.

select distinct
    movie_id,
    {{ dbt_utils.generate_surrogate_key(['lower(company_name)']) }} as production_company_id
from {{ ref('int_movie_companies') }}
