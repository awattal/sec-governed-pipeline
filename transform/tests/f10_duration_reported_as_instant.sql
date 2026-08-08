-- F10: a duration concept reported with no duration.
--
-- period_type = 'D' should pair with qtrs > 0. The dictionary is
-- authoritative on whether a concept is an instant or a duration,
-- so a disagreement is a defect in the fact.
--
-- Monitor, not assertion (F4). Threshold restated against the
-- governed population in F22 - currently 0.246%, warning at 0.5%.
-- The rate lives in monitor_rates in dbt_project.yml and the row
-- count is computed at run time, so it stays meaningful as volume
-- changes.
--
-- Returns failing rows. Empty result = pass.

{{ config(severity = 'warn') }}

select
    n.adsh,
    n.tag,
    n.version,
    n.ddate,
    n.qtrs,
    n.uom,
    n.value,
    t.period_type

from {{ ref('int_num_in_scope') }} n

join {{ ref('stg_tag') }} t
       on t.tag     = n.tag
      and t.version = n.version

where t.period_type = 'D'
  and n.qtrs = 0