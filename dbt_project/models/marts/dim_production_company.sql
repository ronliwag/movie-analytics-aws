-- Deduped production company catalog. production_company_id is a
-- surrogate key hashed from the normalized name -- movie_company.sql
-- computes the same hash independently, so no join is needed to resolve
-- the FK.

with company_names as (

    select distinct company_name from {{ ref('int_movie_companies') }}

),

keyed as (

    select
        {{ dbt_utils.generate_surrogate_key(['lower(company_name)']) }} as production_company_id,
        company_name
    from company_names

)

select
    production_company_id,
    min(company_name) as name
from keyed
group by production_company_id
