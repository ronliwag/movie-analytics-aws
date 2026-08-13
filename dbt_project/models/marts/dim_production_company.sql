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
