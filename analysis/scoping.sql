-- ============================================================
-- scoping.sql
-- Purpose: establish the grain and scope of the modelled layer.
--   profiling.sql asks "what is wrong with this data".
--   This asks "what subset am I building on, and why that one".
-- Data: SEC Financial Statement Data Sets, batch 2025Q4
-- Run:  duckdb -readonly data/sec.duckdb < analysis/scoping.sql \
--         > analysis/scoping_results.txt 2>&1
-- Findings produced: F6-F14
-- ============================================================


-- ------------------------------------------------------------
-- Q1 (F6). Does a single filing report facts for more than one period?
--
-- A filing presents prior-period comparatives alongside current
-- figures, so one filing may carry facts at several period-end dates.
-- If so, a "one row per filer per period" model must filter ddate.
-- ------------------------------------------------------------
with per_filing as (
    select n.adsh,
           s.form,
           count(distinct n.ddate) as distinct_periods
    from num n
    join sub s on s.adsh = n.adsh
    group by 1, 2
)
select form,
       count(*)                        as filings,
       min(distinct_periods)           as min_periods,
       round(avg(distinct_periods), 1) as avg_periods,
       max(distinct_periods)           as max_periods
from per_filing
group by 1
order by filings desc;


-- ------------------------------------------------------------
-- Q2 (F8). What durations exist, and how are rows spread across them?
--
-- qtrs is the number of quarters a value covers: 0 = instant,
-- 1 = three months, 4 = twelve months. ddate is the period end.
-- Mixing durations in one column yields a table that looks correct
-- and is not.
-- ------------------------------------------------------------
select qtrs,
       count(*)                                           as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2) as pct_of_rows
from num
group by 1
order by row_count desc;


-- ------------------------------------------------------------
-- Q3 (F9, F11). Standard vs filer-custom tags, measured on rows.
--
-- F3 measured this on the dictionary. This measures it on the data.
-- LEFT JOIN is deliberate: an INNER JOIN would silently drop any
-- num row absent from the dictionary. The third bucket is a
-- referential integrity check (F11).
-- ------------------------------------------------------------
select coalesce(cast(t.custom as varchar), 'NO MATCHING TAG') as tag_class,
       count(*)                                               as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2)      as pct_of_rows,
       count(distinct n.tag)                                  as distinct_tags
from num n
left join tag t
       on t.tag     = n.tag
      and t.version = n.version
group by 1
order by row_count desc;


-- ------------------------------------------------------------
-- Q4 (F7). Verify the iord domain before building rules on it.
--
-- Q5 tests facts against iord. A rule built on an unverified column
-- domain is the failure documented in F5.
-- ------------------------------------------------------------
select iord,
       count(*) as tag_rows
from tag
group by 1
order by tag_rows desc;


-- ------------------------------------------------------------
-- Q5 (F10). Does each fact's duration match its tag's declared type?
--
-- iord = 'I' should pair with qtrs = 0; iord = 'D' with qtrs > 0.
-- Scoped to standard tags per F9. INNER JOIN is safe here only
-- because Q3 established there are no unmatched rows.
-- ------------------------------------------------------------
select t.iord,
       case when n.qtrs = 0 then 'instant (qtrs = 0)'
            else 'duration (qtrs > 0)'
       end                   as fact_shape,
       count(*)              as row_count,
       count(distinct n.tag) as distinct_tags
from num n
join tag t
       on t.tag     = n.tag
      and t.version = n.version
where t.custom = 0
group by 1, 2
order by 1, 2;


-- ------------------------------------------------------------
-- Q6 (F10, sample). Inspect the violating rows.
--
-- Counts establish that a violation class exists; they do not
-- establish that it is a defect. version and coreg are selected
-- because they are part of the num primary key — without them,
-- two distinct records are indistinguishable in the output.
-- ------------------------------------------------------------
select n.tag,
       n.version,
       n.coreg,
       t.iord,
       n.qtrs,
       n.adsh,
       n.ddate,
       n.uom,
       n.value
from num n
join tag t
       on t.tag     = n.tag
      and t.version = n.version
where t.custom = 0
  and t.iord   = 'D'
  and n.qtrs   = 0
order by n.tag, n.adsh
limit 25;

-- ------------------------------------------------------------
-- Q7 (F12). Does num honour its primary key?
--
-- PK read from `describe num`, not from documentation: adsh, tag,
-- version, ddate, qtrs, uom, segments, coreg. An earlier run of this
-- query omitted `segments` and reported 2,458,926 affected rows —
-- a 24,000-fold overstatement. See the failure analysis.
--
-- count(distinct value) separates exact duplicates from records that
-- share a key and disagree on the value.
-- ------------------------------------------------------------
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


-- ------------------------------------------------------------
-- Q8 (F12). Does the key hold on the consolidated population?
--
-- All Q7 violations carry a non-null segments. This tests the rows a
-- company-period model would actually consume. Returns zero.
-- ------------------------------------------------------------
with keyed as (
    select adsh, tag, version, ddate, qtrs, uom, coreg,
           count(*) as row_count
    from num
    where segments is null
    group by 1, 2, 3, 4, 5, 6, 7
    having count(*) > 1
)
select count(*)       as key_groups,
       sum(row_count) as affected_rows
from keyed;


-- ------------------------------------------------------------
-- Q9 (F13). Which taxonomies does the standard-tag population span?
--
-- custom = 0 means "in a recognised taxonomy", not "us-gaap".
-- split_part collapses version years (us-gaap/2024, us-gaap/2025)
-- into one family.
-- ------------------------------------------------------------
select split_part(t.version, '/', 1)                      as taxonomy,
       count(*)                                           as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2)  as pct_of_rows,
       count(distinct n.tag)                              as distinct_tags
from num n
join tag t
       on t.tag     = n.tag
      and t.version = n.version
where t.custom = 0
group by 1
order by row_count desc;


-- ------------------------------------------------------------
-- Q10 (F14). Consolidated vs dimensional facts.
--
-- segments carries the dimensional breakdown of a value. Null means
-- a consolidated total. Selecting a concept without constraining
-- segments returns an arbitrary row and raises no error.
-- ------------------------------------------------------------
select case when segments is null then 'consolidated (segments null)'
            else 'dimensional (segments present)'
       end                                                as fact_level,
       count(*)                                           as row_count,
       round(100.0 * count(*) / sum(count(*)) over (), 2)  as pct_of_rows,
       count(distinct tag)                                as distinct_tags
from num
group by 1
order by row_count desc;


-- ------------------------------------------------------------
-- Q11 (F14). Do headline concepts appear at both levels?
--
-- If so, a pivot to company-period grain must filter segments.
-- Filing counts also give coverage, which constrains any mart
-- column list.
-- ------------------------------------------------------------
select n.tag,
       count(*) filter (where n.segments is null)     as consolidated_rows,
       count(*) filter (where n.segments is not null) as dimensional_rows,
       count(distinct n.adsh)                         as filings
from num n
where n.tag in ('Assets', 'Liabilities', 'StockholdersEquity',
                'Revenues', 'NetIncomeLoss')
group by 1
order by 1;