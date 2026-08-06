select iord,
       count(*) as tag_rows
from tag
group by 1
order by tag_rows desc;


select t.iord,
       case when n.qtrs = 0 then 'instant (qtrs = 0)'
            else 'duration (qtrs > 0)'
       end                   as fact_shape,
       count(*)              as row_count,
       count(distinct n.tag) as distinct_tags
from num n
join tag t
  on  t.tag     = n.tag
  and t.version = n.version
where t.custom = 0
group by 1, 2
order by 1, 2;

-- Does num honour its primary key?
-- PK per the actual schema: adsh, tag, version, ddate, qtrs, uom, segments, coreg
with keyed as (
    select adsh, tag, version, ddate, qtrs, uom, segments, coreg,
           count(*)              as row_count,
           count(distinct value) as distinct_values
    from num
    group by 1, 2, 3, 4, 5, 6, 7, 8
    having count(*) > 1
)
select case when distinct_values = 1 then 'exact duplicate'
            else 'conflicting values'
       end            as violation_type,
       count(*)       as key_groups,
       sum(row_count) as affected_rows
from keyed
group by 1
order by key_groups desc;


describe num;

with keyed as (
    select adsh, tag, version, ddate, qtrs, uom, segments, coreg,
           count(*)              as row_count,
           count(distinct value) as distinct_values
    from num
    group by 1, 2, 3, 4, 5, 6, 7, 8
    having count(*) > 1
      and count(distinct value) > 1
)
select n.adsh, n.tag, n.ddate, n.qtrs, n.uom, n.segments, n.value
from num n
join keyed k
  on  k.adsh    = n.adsh
  and k.tag     = n.tag
  and k.version = n.version
  and k.ddate   = n.ddate
  and k.qtrs    = n.qtrs
  and k.uom     = n.uom
  and coalesce(k.segments, '') = coalesce(n.segments, '')
  and coalesce(k.coreg, '')    = coalesce(n.coreg, '')
order by n.adsh, n.tag, n.ddate;


with keyed as (
    select adsh, tag, version, ddate, qtrs, uom, coreg,
           count(*) as row_count
    from num
    where segments is null
    group by 1, 2, 3, 4, 5, 6, 7
    having count(*) > 1
)
select count(*) as key_groups, sum(row_count) as affected_rows
from keyed;

select split_part(t.version, '/', 1)                     as taxonomy,
       count(*)                                          as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2) as pct_of_rows,
       count(distinct n.tag)                             as distinct_tags
from num n
join tag t
       on t.tag     = n.tag
      and t.version = n.version
where t.custom = 0
group by 1
order by row_count desc;

select case when segments is null then 'consolidated (segments null)'
            else 'dimensional (segments present)'
       end                                               as fact_level,
       count(*)                                          as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2) as pct_of_rows,
       count(distinct tag)                               as distinct_tags
from num
group by 1
order by row_count desc;

select n.tag,
       count(*) filter (where n.segments is null)     as consolidated_rows,
       count(*) filter (where n.segments is not null) as dimensional_rows,
       count(distinct n.adsh)                         as filings
from num n
where n.tag in ('Assets', 'Liabilities', 'StockholdersEquity',
                'Revenues', 'NetIncomeLoss')
group by 1
order by 1;