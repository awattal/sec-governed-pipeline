# Backlog

Open work items. Findings go in FINDINGS.md; this is work owed.

## Blocking W3

The agent loop can't be trusted without these.

- **Severity definitions.** Every violation currently counts as one.
  3,425 F10 violations in shell companies and 3,425 in large filers
  are the same number to the pipeline. `value` and filer size are
  available to classify on. Decide before the agent generates rules —
  retrofitting means regenerating everything it has produced.
- **The agent's action space.** If the agent emits free-form SQL it
  cannot be evaluated, diffed or bounded. A constrained structure —
  test type from a fixed vocabulary, column, parameters — is
  reviewable and comparable across runs. Decide deliberately rather
  than letting the prompt decide it.
- **Run history table**, carrying a population dimension (in scope /
  out of scope). Everything downstream depends on it: drift, batch
  comparison, out-of-scope recording, and the agent's own results.
- `run_test` returns every node in `run_results.json`, not just the
  selector's. Selecting a model pulls in tests that merely reference
  it. The agent asks about one rule and gets ten results with no way
  to know which answers its question.
- The script discards dbt's stdout, so a compilation error surfaces
  as `NO DATA` with no reason. The difference between an agent that
  can self-correct and one that stalls.


## Do when convenient

- `store_failures` has no row limit. dbt's `limit` caps the reported
  count rather than the stored rows, so it was removed. A generated
  rule failing on millions would write millions — needs a limit
  inside the test SQL, or post-run cleanup. Becomes urgent when the
  agent starts generating.
- Makefile for the `transform/` vs repo-root split.
- `_staging.yml`: the taxonomy column description should note that
  custom tags carry an accession number, not a taxonomy name.
- `_sources.yml`: the tag source documents four columns; `stg_tag`
  now consumes `crdr` and `datatype`, which are undocumented.
- Fixture column type inference. DuckDB read_csv infers types from the
  data it sees. A column that is entirely null in the fixture may be
  typed differently than in the full file, so a model can pass in CI and
  fail locally, or the reverse. If it bites, declare explicit column
  types in ingest.py rather than inferring.
- Rate-based monitors on a small population. config/monitors.yml holds
  tolerances as rates. On a few thousand fixture rows a single row moves
  the rate far more than it does on 3.8m. Decide whether CI judges
  monitors at all, or only asserts.
- Referential test vacuity in CI. The fixture prunes tag to rows
  referenced by num, so any num-to-tag relationship test passes by
  construction. It can still catch model logic regressions, not data
  regressions. State this limitation in the README alongside the
  fixture description.
- requirements.txt is a full pip freeze including transitive
  dependencies. Reproducible, but upgrading any single package is
  awkward. Consider a direct-dependency file compiled to a lock file
  if maintenance becomes painful. Not urgent.
- Negative fixture. The CI fixture is valid data and exercises only
  code-regression tests. Defect-catching tests (period_end_date
  not_null as the F1 control) cannot be exercised by data the pipeline
  passes on. A separate negative fixture with assert-failure tests
  would prove those controls work. Not W3.
- Test count discrepancy. Declared tests across the three YAML files
  appear to exceed the recorded 35. Reconcile.
- F10 test comment is stale. It states the rate lives in monitor_rates
  in dbt_project.yml and the row count is computed at run time. That
  describes the abandoned macro approach. W2 moved threshold judgement
  to run_dbt_test.py against config/monitors.yml. Correct the comment.
- Config location inconsistency. The F10 comment cites dbt_project.yml
  monitor_rates; the W2 design cites config/monitors.yml. Confirm which
  is live and remove the other reference.
- Custom test names. The alias config key on the two expression_is_true
  tests was silently ignored; dbt generated its own names. Auto-names
  are adequate but unwieldy. Use the name: key at test level if
  deliberate naming becomes necessary for the agent's node matching.
- coreg is inert in the PK. No group in 2025Q4 differs on coreg alone,
  so removing it from the key test is undetectable. Re-test when a
  second quarter lands.
- abstract flag is constant in 2025Q4 (F26). is_abstract cast is
  unexercised for true. Re-check on second quarter before concluding
  the column is inert.
- make_fixture.py profiler prints GAP marker on expected-zero checks
  even though they are excluded from the gap list. Cosmetic.


## Parked

- **Out-of-scope monitoring.** Out-of-scope rows remain in staging by
  design (F22) but are untested. Recording starts with the run
  history table above — out-of-scope tests at warn severity, results
  captured with a population column. Thresholds and drift wait for a
  second quarter: a rate with no trend behind it cannot be monitored,
  but it can be recorded, and it has to be recorded before the moment
  you want to look back at it. Mechanism undecided — warn-severity
  tests, a separate `int_num_out_of_scope` model, or reporting off
  the run history.
- **Multi-quarter load, and point-in-time vs current-view mart
  semantics.** W5. The design decision the second quarter forces.
- **F24 candidate:** 6,003 us-gaap tags in the dictionary against
  4,030 used in `num` — a third of the standard vocabulary is unused
  this quarter. Same shape as F9. Promote or drop; "not yet written
  up" is where observations go to die.
- Periodic full-volume run. CI proves correctness on a fixture, not
  behaviour at 3.8m rows. Consider a scheduled workflow that ingests the
  real quarter and runs the suite, separate from the per-push gate.


## Write-up material

Not work. Notes for the W5 failure analysis.

- `store_failures` earned its place immediately: `Got 50 results`
  reads as systemic, but all 50 were one filer's dimensional rows.
  The count alone points at the wrong conclusion — a worked example
  of why a counting test is insufficient input for an agent.
- The threshold macro that could not work. dbt resolves test configs
  at parse time, so the macro returned its placeholder and `warn_if`
  was silently `> 0` for a run. Caught only by checking the count
  directly rather than trusting a green result.
- `_display_name` returned an empty string for singular tests, which
  silently disabled the monitor lookup. Plausible-looking output, no
  error. F5's shape again.