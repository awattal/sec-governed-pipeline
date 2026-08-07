-- One row per SEC submission. Cleans the raw sub table:
-- casts the integer date columns to real dates (F1) and
-- restricts the column list to what the modelled layer uses.

with source as (

    select * from {{ source('sec_raw', 'sub') }}

),

renamed as (

    select
        -- identifiers
        adsh,
        cik,
        name              as registrant_name,
        sic               as sic_code,
        countryba         as business_country,

        -- filing metadata
        form              as form_type,
        fy                as fiscal_year,
        fp                as fiscal_period,

        -- dates: stored as yyyymmdd integers in the source (F1)
        cast(strptime(cast(period  as varchar), '%Y%m%d') as date) as period_end_date,
        cast(strptime(cast(filed   as varchar), '%Y%m%d') as date) as filed_date,
        cast(strptime(cast(changed as varchar), '%Y%m%d') as date) as changed_date,

        -- flags: left as integers so the {0,1} domain test (F2)
        -- asserts what the source actually contains
        wksi,
        prevrpt,
        detail,

        -- provenance, added by scripts/ingest.py
        quarter

    from source

)

select * from renamed