-- Profiling queries: SEC Financial Statement Data Sets
-- Batch: 2025Q4
-- Run: duckdb data/sec.duckdb < analysis/profiling.sql

.print === F1: Date fields typed as BIGINT ===
SELECT period, filed, changed FROM sub LIMIT 5;

.print === F2: Boolean fields - domain check ===
SELECT 'wksi' AS field, wksi AS value, COUNT(*) AS n FROM sub GROUP BY wksi
UNION ALL
SELECT 'prevrpt', prevrpt, COUNT(*) FROM sub GROUP BY prevrpt
UNION ALL
SELECT 'detail', detail, COUNT(*) FROM sub GROUP BY detail
ORDER BY field, value;

.print === F3: Date format validity ===
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE LENGTH(CAST(period AS VARCHAR)) <> 8) AS bad_length,
  COUNT(*) FILTER (WHERE (period // 100) % 100 NOT BETWEEN 1 AND 12) AS bad_month,
  COUNT(*) FILTER (WHERE period % 100 NOT BETWEEN 1 AND 31) AS bad_day
FROM sub;

.print === F4: Custom vs standard tags ===
SELECT custom, COUNT(*) AS n FROM tag GROUP BY custom;

.print === F5: Custom tag reuse across submissions ===
WITH tag_usage AS (
  SELECT n.tag, COUNT(DISTINCT n.adsh) AS submissions
  FROM num n
  JOIN tag t ON n.tag = t.tag AND n.version = t.version
  WHERE t.custom = 1
  GROUP BY n.tag
)
SELECT
  COUNT(*) AS custom_tags_used,
  COUNT(*) FILTER (WHERE submissions = 1) AS used_once,
  COUNT(*) FILTER (WHERE submissions > 10) AS used_over_10,
  MAX(submissions) AS max_submissions
FROM tag_usage;