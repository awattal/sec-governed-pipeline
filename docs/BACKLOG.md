# Backlog

Open work items. Findings go in FINDINGS.md. Settled decisions go in
DECISIONS.md. This is work owed.

Sections are ordered by what they block. Cut from the bottom.

## Blocks the loop

Step 2 cannot be built or trusted without these.

- **Tag selection basis.** Thousands of in-scope tags; the agent
  cannot be pointed at all of them. Needs a stated basis for which
  tags get proposals first — frequency, CDE candidacy, or deliberate
  coverage of the nine check types. This is a governance decision
  about where control effort goes first, not a technical one.
- `run_test` returns every node in `run_results.json`, not just the
  selector's. Selecting a model pulls in tests that merely reference
  it. The agent asks about one rule and gets ten results with no way
  to know which answers its question. Related to the custom test
  names item under Polish — the fix for one may be the fix for both.
- The script discards dbt's stdout, so a compilation error surfaces
  as `NO DATA` with no reason. This is the difference between an
  agent that can self-correct and one that stalls.
- `store_failures` has no row limit. dbt's `limit` caps the reported
  count rather than the stored rows, so it was removed. An
  agent-generated rule failing on millions of rows would write
  millions. Needs a limit inside the test SQL, or post-run cleanup.
  Was "becomes urgent when the agent starts generating" — that is
  now next session.
- Rejected proposals must be retained, not discarded. The `wrong`
  disposition is the precision denominator. If rejected rules are
  deleted, the headline eval metric cannot be computed.

## Blocks the eval

- **Run history table.** Carries a population dimension (in scope /
  out of scope), the baseline count set at acceptance, and the rule
  version the finding was produced under. Everything downstream
  depends on it: drift, batch comparison, out-of-scope recording,
  and the agent's own results.
  Also carries impact attributes. 3,425 F10 violations in shell
  companies and 3,425 in large filers currently read identically to
  the pipeline. `value` and filer size are available to record
  against a finding. This is a recorded attribute, not a severity
  input.
- **Multi-quarter load (2025Q3).** Moved out of Parked. The holdout
  decision makes this load-bearing: rules proposed from Q4 are
  evaluated against Q3, and without it there is no evidence the
  agent's rules generalise beyond the quarter they were written
  from. Forces the point-in-time vs current-view mart decision.
- Negative fixture. The CI fixture is valid data and exercises only
  code-regression tests. Defect-catching tests (period_end_date
  not_null as the F1 control) cannot be exercised by data the
  pipeline passes on. A separate negative fixture with
  assert-failure tests would prove those controls work.
- Rate-based monitors on a small population. config/monitors.yml
  holds tolerances as rates. On a few thousand fixture rows a single
  row moves the rate far more than it does on 3.8m. Decide whether
  CI judges monitors at all, or only asserts.
- Referential test vacuity in CI. The fixture prunes tag to rows
  referenced by num, so any num-to-tag relationship test passes by
  construction. It catches model logic regressions, not data
  regressions. State this limitation in the README alongside the
  fixture description.

## Polish

Real, not urgent. Most of this will not get done before 31 August.
That is acceptable if decided rather than discovered.

- Delete or rewrite docs/severity.md. Written under the S1/S2/S3
  model, superseded 11 Aug and again 15 Aug. A stale design doc
  misrepresents the system and is worse than none.
- Reframe the 37 hand-written dbt tests in the README as the
  human-authored control set — the baseline agent proposals are
  compared against, not the model for how rules get written going
  forward.
- Backfill pre-11 Aug decisions into DECISIONS.md: scope as a model
  not a filter, flags not filters, measurement separate from
  judgement, rates over row counts, hard-coded fixture filers.
  Currently these live only in commit messages and code comments.
- README does not state that structural checks are the deliberate
  floor and business-logic checks are the agent's target.
- `_sources.yml` documents four tag columns; `stg_tag` now consumes
  `crdr` and `datatype`, which are undocumented. More than a
  tidy-up: these two columns are what make sign and additivity
  derivable without a language model, and they are the direct
  counter-argument to the project's own justification for using
  one. Document them and handle the argument in the README rather
  than meeting it in an interview.
- Test count discrepancy. Declared tests across the three YAML files
  appear to exceed the recorded count; the backlog has previously
  said both 35 and 37. Reconcile and use one number.
- F10 test comment is stale and cites monitor_rates in
  dbt_project.yml, which describes the abandoned macro approach. W2
  moved threshold judgement to run_dbt_test.py against
  config/monitors.yml. Correct the comment and remove the dead
  reference. (Merged with the former "config location
  inconsistency" item — same issue.)
- Custom test names. The alias config key on the two
  expression_is_true tests was silently ignored; dbt generated its
  own names. Auto-names are adequate but unwieldy. Use the name: key
  at test level if deliberate naming becomes necessary for the
  agent's node matching. See the `run_test` item under Blocks the
  loop.
- docs/ci.md. What the workflow runs, what a green tick asserts, the
  fixture's composition and coverage profile, branch protection.
  DECISIONS.md now covers what docs/design.md was for, so only ci.md
  remains outstanding.
- Published issue register (rule, disposition state, owner, rate) as
  the human-facing consumer of findings. Was written against
  severity; severity is gone.
- Makefile for the `transform/` vs repo-root split.
- `_staging.yml`: the taxonomy column description should note that
  custom tags carry an accession number, not a taxonomy name.
- Fixture column type inference. DuckDB read_csv infers types from
  the data it sees. A column entirely null in the fixture may be
  typed differently than in the full file, so a model can pass in CI
  and fail locally, or the reverse. If it bites, declare explicit
  column types in ingest.py.
- requirements.txt is a full pip freeze including transitive
  dependencies. Reproducible, but upgrading a single package is
  awkward. Consider a direct-dependency file compiled to a lock file
  if maintenance becomes painful.
- make_fixture.py profiler prints GAP marker on expected-zero checks
  even though they are excluded from the gap list. Cosmetic.

## Parked

- **Out-of-scope monitoring.** Out-of-scope rows remain in staging by
  design (F22) but are untested. Recording starts with the run
  history table — out-of-scope tests at warn severity, results
  captured with a population column. Thresholds and drift need the
  second quarter: a rate with no trend behind it cannot be
  monitored, but it can be recorded, and it has to be recorded
  before the moment you want to look back at it. Mechanism
  undecided.
- Periodic full-volume run. CI proves correctness on a fixture, not
  behaviour at 3.8m rows. Consider a scheduled workflow that ingests
  the real quarter and runs the suite, separate from the per-push
  gate.
- `coreg` is inert in the PK. No group in 2025Q4 differs on `coreg`
  alone, so removing it from the key test is undetectable. Re-test
  when a second quarter lands.
- `abstract` flag is constant in 2025Q4 (F26). `is_abstract` cast is
  unexercised for true. Re-check on the second quarter before
  concluding the column is inert.

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