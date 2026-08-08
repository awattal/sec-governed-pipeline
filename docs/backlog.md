# Backlog

Open items, newest first. Findings go in FINDINGS.md; this is work.

## Tests
- `equal_rowcount` on stg_num once built

## Documentation
- README: `dbt deps` is a required setup step
- README: VS Code DuckDB extension holds an exclusive lock regardless
  of readOnly — disconnect before any dbt run
- README: data/sec.duckdb must be built locally, it is not committed
- README: scope statement citing F13/F19/F14, pointer to FINDINGS.md
- `_staging.yml`: taxonomy column description should note that custom
  tags carry an accession number, not a taxonomy name (91% of rows)
- `_sources.yml`: tag source documents 4 columns; stg_tag now consumes
  crdr and datatype, which are undocumented

## Observations not yet written up
- 6,003 us-gaap tags in the dictionary vs 4,030 used in num — a third
  of the standard vocabulary is unused this quarter. Same shape as F9.

## Deferred by decision
- Makefile for the transform/ vs repo-root directory split (W3)
- store_failures on generated tests (with the F10 test)
- `conclusive` property on TestResult (F16, with the F10 test)
- Run history table, rule registry, exception register (W3)
- Multi-quarter load and point-in-time vs current-view (W5)