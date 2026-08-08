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