-- Dictionary of reporting concepts. One row per (tag, version).
-- 1:1 with source: no filtering, so excluded taxonomies stay
-- testable (F21).

select
    tag,
    version,
    split_part(version, '/', 1) as taxonomy,

    custom   = 1                as is_custom,
    abstract = 1                as is_abstract,

    datatype,
    iord                        as period_type,
    crdr                        as balance_type,
    tlabel                      as label,
    doc                         as definition

from {{ source('sec_raw', 'tag') }}