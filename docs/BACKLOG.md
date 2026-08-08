# Backlog

Open items, newest first. Findings go in FINDINGS.md; this is work.

## Tests
- `equal_rowcount` on stg_num once built
- Measure `dbt test` timing against stg_num as a view; switch to
  `materialized: 'table'` only if the number justifies it. Decision
  deferred deliberately — record the measurement, not just the choice.
- stg_num materialisation: measured. 14 tests in 3.4s as a view,
  key test 0.33s across 3.8M rows. Staying a view; revisit only if
  the agent loop shows it matters.
- run_test returns every node in run_results.json, not just the
  selector's. Selecting a model pulls in tests that merely reference
  it (F10 appears under stg_tag). The agent needs to know which
  result answers its question — filter or tag by requested selector.
- The script discards dbt's stdout, so a compilation error surfaces
  as `NO DATA` with no reason. Capture stdout on non-conclusive
  results.
- store_failures limit removed: dbt applies `limit` to the test
  query itself, capping the reported count, not just stored rows.
  F10 reported 500 instead of 3,425. Needs a different guard against
  unbounded failure tables from generated rules.

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
- store_failures earned its place immediately: `Got 50 results` reads
  as systemic, but all 50 are one filer's dimensional rows. The count
  alone points at the wrong conclusion. Worked example for the W5
  write-up on why the agent needs sample rows, not counts.
- store_failures limit removed: dbt applies `limit` to the test
  query itself, so it caps the reported failure count, not just the
  stored rows. F10 reported 500 instead of 3,425. Need a different
  guard against unbounded failure tables from generated rules —
  possibly a limit inside the test SQL, or post-run cleanup.

## Deferred by decision
- Makefile for the transform/ vs repo-root directory split (W3)
- store_failures on generated tests (with the F10 test)
- `conclusive` property on TestResult (F16, with the F10 test)
- Run history / rule registry carries a population dimension:
  governed (us-gaap consolidated) vs observed (everything else).
  Same rule definition runs against both; only governed results
  carry exceptions, thresholds and drift tracking. Registry needs
  a field for which populations a rule applies to.
- Multi-quarter load and point-in-time vs current-view (W5)
- stg_num: consider a derived `is_in_scope` column (is_us_gaap and
  is_consolidated) so test `where` configs reference one flag rather
  than repeating the conjunction. Decide before the F10 test.

  ## Out-of-scope monitoring — deferred, not dropped

The pipeline governs us-gaap consolidated facts. Out-of-scope rows
remain in staging by design (F22) but are currently untested and
unmonitored. Decided to defer rather than build alongside the
governed path.

- Decide the mechanism: warn-severity tests, a separate
  int_num_out_of_scope model, or reporting off the run history
- Key uniqueness on out-of-scope rows: 50 groups, one filer (F23).
  Test removed from stg_num rather than kept as a warning
- F10 out-of-scope rate is 0.935% vs 0.246% governed (F22) — the
  observational series that would show drift
- Recording starts W3 with the run history table: out-of-scope tests
  run at warn severity, results captured with a population column.
  Thresholds and drift detection wait for Q3 — a rate with no trend
  behind it cannot be monitored, but it can be recorded, and it has
  to be recorded before the moment you want to look back at it





  