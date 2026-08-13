with extended as (

    select movie_id, production_country_codes, production_country_names
    from {{ ref('stg_movie_extended') }}
    where production_country_codes is not null

)

select distinct
    movie_id,
    trim(country_code) as country_code,
    nullif(trim(country_name), '') as country_name
from extended,
    unnest(
        string_to_array(production_country_codes, ','),
        string_to_array(production_country_names, ',')
    ) as t(country_code, country_name)
where trim(country_code) ~ '^[A-Za-z]{2}$'
