-- Reported numeric facts. One row per (adsh, tag, version, ddate,
-- qtrs, uom, coreg, segments) -- see F14 for why segments belongs
-- in that key.
--
-- 1:1 with source: scope is expressed as flags, not filters, so
-- excluded rows stay testable. F22 measured the cost of getting
-- this wrong -- 19,195 F10 violations sit in the rows the
-- consolidated filter removes.

select
    adsh,
    tag,
    version,
    split_part(version, '/', 1)             as taxonomy,

    coreg,
    segments,

    ddate,
    strptime(cast(ddate as varchar), '%Y%m%d')::date as period_end_date,
    qtrs,

    uom,
    value,
    footnote,

    split_part(version, '/', 1) = 'us-gaap' as is_us_gaap,
    segments is null                        as is_consolidated,
    coreg    is null                        as is_parent_only,

    quarter

from {{ source('sec_raw', 'num') }}
