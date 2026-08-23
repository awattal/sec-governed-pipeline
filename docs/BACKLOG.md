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
- Proposal schema is missing the row filter. target names the column
  (int_num_in_scope.value) but not the population. Every check needs
  tag = '<concept>' and the filter currently exists only in prompt
  prose. Add a structured filter field before compile_rules.py.

- assertion shapes are unconstrained. First sign proposal returned
  {direction: non_negative}; nothing prevents a different shape next
  time. Fix a per-check-type assertion schema after the first batch,
  when real shapes are known for several types. Validator currently
  checks only that assertion is an object.

## Blocks the eval

- Findings table in DuckDB: run_id, run_at, quarter, rule_id,
  rule_version, population, rows_evaluated, rows_failed. Rate is
  computed at report time, never stored, so the denominator stays
  visible. Written by run_dbt_test.py. Dispositions are not held
  here — they live in the rule YAML under version control.
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
- API key expires ~15 Sep 2026. propose.py will fail with an auth
  error after that date. Setup docs must state that a key is
  required and how to obtain one, so the failure is diagnosable
  rather than mysterious. Findings and rules remain readable
  without a key — only new proposals need one.
- model field records the alias claude-sonnet-5, not a dated model
  identifier. The alias resolves to different weights over time, so
  two proposals recording the same value may not have come from the
  same model. Check whether the API exposes a resolved dated
  identifier; if it does, record that instead. If it does not, state
  the limitation in the README rather than implying provenance is
  tighter than it is.
- propose.py reads column names from stg_tag directly. Two failed
  runs this session came from the script and the staging model
  disagreeing on names. The element lineage list (W3) is the record
  of source-to-model renames and would have prevented both. Note as
  evidence the artifact earns its keep.

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
- CDE criteria (identifies a record, carries a value, scopes the
  population, places a value in time) apply to columns, not tags.
  The framework has been written against tags in places. Correct
  before it reaches the README. Tag-level criticality needs a
  separate basis — statement structure is the working one.

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

  ## Blocks the proposal loop

- Proposal schema is missing the row filter. `target` names the column
  (`int_num_in_scope.value`) but not the population. Every check needs
  `tag = '<concept>'`; the filter currently exists only in prompt prose.
  Add a structured filter field before `compile_rules.py`.

- `assertion` shapes are unconstrained. The first `sign` proposal
  returned `{direction: non_negative}`; nothing prevents a different
  shape next time. Fix a per-check-type assertion schema after the
  first batch, when real shapes are known across several types.

- `propose_v2.md` asks the model to originate assertions with no
  declared business intent as input. Inconsistent with the position
  that business supplies intent and the agent scales it. Add an intent
  parameter before the volume run.

- `propose_v2.md` and the multi-check `propose.py` are written but not
  yet run. Both schema questions above are unanswered by any output.

- `rules/proposed/accountspayablecurrent__sign.yml` is a v1 artifact
  with no `dimension` field. Inconsistent with the v2 schema.
  Regenerate or delete; do not promote.

- Tag selection for proposals is a heuristic (statement-structure
  tags), not a designation. Replace with CDE-derived selection before
  any volume run, or the rule set has no defensible basis for scope.

- CDE-aware proposal depth. Critical elements should attract a fuller
  rule family than non-critical ones. Not implementable until CDE
  designation exists. Until then the cap of five applies uniformly;
  afterwards the cap becomes a function of criticality.

## Blocks the eval

- Dimension over-claim is expected and should be measured, not
  prevented. `accuracy` requires a reference source the pipeline does
  not hold; `timeliness` is not testable by a value check. Count how
  often each is claimed and report it.

## Polish

- API key expires ~15 Sep 2026. `propose.py` will fail with an auth
  error after that date. Setup docs must state that a key is required
  and how to obtain one, so the failure is diagnosable. Findings and
  rules remain readable without a key.

- `model` field records the alias `claude-sonnet-5`, not a dated
  identifier. The alias resolves to different weights over time, so
  two proposals recording the same value may not share a model. Check
  whether the API exposes a resolved dated identifier; if not, state
  the limitation in the README.

- `docs/CDE.md` must state that blanket upstream inheritance produces
  a CDE count above the 10-15% banking benchmark, because derivation
  chains converge on shared sources (`version` feeds both `taxonomy`
  and `is_us_gaap`). Otherwise the count reads as a miscalibrated
  threshold.

- `pre` is ingested and read by no model; all 10 SEC columns unused.
  Either build a model on it or note in the README that it is staged
  for statement-structure work.

- Two failed runs this session came from `propose.py` and `stg_tag`
  disagreeing on column names. `docs/LINEAGE.md` is the record of
  source-to-model renames and would have prevented both. Evidence the
  artifact earns its keep.
- Baseline technical rules generated from CDE designation and lineage,
  not proposed by the LLM. Keys get not_null and unique; join columns
  get relationship checks. Derivable from structure, so deriving them
  is correct and proposing them would be waste. Draws the boundary of
  what the LLM is for.

- Re-designation on model change. New or changed models regenerate
  lineage, which invalidates CDE scores. Scoring cannot be automated -
  two of three factors are human ratings - so the pipeline detects
  staleness and flags elements needing rating rather than re-scoring
  them. Document the process in CDE.md; implement the staleness check
  only if time allows.

  ## Blocks the use case loop

- config/use_cases.yml does not exist. Use cases are currently
  recorded only in docs/CDE.md prose. Needed before UC-2, since
  rule_id prefixes and the findings rollup both key on use case ID.

- identify_targets.py does not exist. Given a use case sentence, the
  LLM must identify which physical elements it applies to and any row
  filter. This is semantic work, not lineage traversal - "interest
  rate below 50% for lending BU" requires mapping business terms to
  columns. Target list must be reviewable before rules are proposed;
  a wrong target produces confidently wrong rules.

- propose.py has no use_case parameter. Rules it generates cannot be
  attributed to a use case or prefixed correctly in rule_id.

## Blocks findings

- compile_rules.py does not exist. Converts rules/active/*.yml into
  executable dbt tests. Two approaches unresolved: generate one .sql
  file per rule into transform/tests/ (readable, greppable, but 20+
  generated files in the repo), or one generic macro reading YAML at
  runtime (clean repo, opaque tests).

- Findings storage unbuilt. Two tables designed, neither created:
  rule_registry (current state, rebuilt from YAML each run) and
  findings (run_id, rule_id, rule_version, rows_checked, rows_failed,
  run_at). rule_version is the git short SHA, joining a finding to
  the exact rule text that produced it.

- No rollup view. The point of the use_case field is that a business
  owner can ask whether their report is trustworthy and get an answer.
  Cheapest defensible version is a generated docs/CONTROLS.md showing
  every rule, its use case, last run and pass rate.

## Journey gaps

- Rule amendment path. A finding can mean the data is wrong or the
  rule is wrong. Disposition handles the first; the second needs a
  route back to the rule itself. F27 (the accounts payable sign rule
  that will fire on valid filings) is the concrete case.

- Rule owner. Every active rule needs a named owner, or findings
  accumulate unattended.

- Requester, reviewer and approver are distinct roles. The PR
  mechanism enforces this structurally; state it in the README rather
  than leaving it implicit.

## Polish

- Null rate on int_num_in_scope.value measured at 2.65% (36,864 of
  1,393,562). Filers can tag a concept and report no amount, so these
  are not defects. Tolerance unset - decide at rule promotion whether
  accepted-with-baseline or investigated.

- config/cde.yml and docs/CDE.md can drift. The config is the
  operative designation; the document holds the reasoning. Add a check
  that every element in the config appears in the document's matrix,
  or state the drift risk in the README.

- Rule folders are lifecycle stages (proposed, active), not origin
  buckets. Origin, basis and use_case are fields on the rule.
  Considered and rejected a separate rules/baseline/ directory, which
  would have mixed the two axes.

- README must state that the repository was authored in collaboration
  with an LLM: code, documentation and rule text drafted by the model,
  reviewed and corrected by the author. Distinct from the runtime
  claim that generate_baseline.py makes no model call. A governance
  case study that is unclear about its own authorship invites the
  obvious question.

- Withdrawn (22 Aug). The item claiming propose_v2.md lets the model
  originate business rules with no declared intent is wrong. The
  declared intent is the nine-type check vocabulary and the CDE
  scope, both settled and in the repo. The agent proposes inside a
  bounded action space and every proposal is reviewed. No per-run
  intent parameter is needed.

- Open: review volume. v2 permits five checks per concept. Batch
  size across the in-scope tag set is unknown until a run happens.
  If the batch exceeds what can be reviewed properly, the review
  control is nominal. Answer after the single-tag run.

- README is written last, after the loop closes. It argues why the
  project matters and needs real findings to point at. Mechanism
  description lives in docs/ARCHITECTURE.md and is written now.

- Additivity proposals name component concepts inferred from
  definitions. pre.txt carries the filer's actual presentation
  structure and reaches no model, so nothing verifies a proposed
  component set against how the filing was presented. Human review
  is the only check. Exposing pre is a candidate extension, not in
  current scope.

- Verify the 20 uc1__ baseline rules conform to the shapes declared
  in config/check_types.yml. They were generated before the config
  existed. If field names diverge, either regenerate them or the
  compiler handles two formats. Check before compile_rules.py.

- rules/rejected/ currently mixes two different things: replies that
  broke the check-type constraint, and replies that failed for
  mechanical reasons (truncation, malformed JSON). Only the first is
  governance evidence. Separate them, or tag the reason type, before
  the volume run. Delete the 2026-08-23 truncation artifact.

- Re-running propose.py on a tag overwrites existing proposals with
  no warning. A reviewed proposal can be silently replaced by a new
  one from a different prompt version. Confirmed on
  accountspayablecurrent__sign.yml, replaced v1 output with v2.
  Recoverable from git, but the run should refuse or version instead.

- First propose_v2 run, AccountsPayableCurrent, three proposals.
  All three rejected at review. Two input gaps identified:

  (a) The prompt gives the model no target schema. The unique
      proposal named columns entity, period, dimensions/axis — none
      exist in int_num_in_scope. Any check requiring a column name
      is guesswork without the schema.

  (b) The prompt gives the model no view of existing controls. The
      not_null proposal duplicates a hand-written dbt test and a
      uc1__ baseline rule. The model cannot distinguish uncovered
      from already covered.

- Second confirmed false positive on AccountsPayableCurrent sign,
  now from both v1 and v2. Vendor overpayment produces a legitimate
  debit balance. The model reasons from the definition and does not
  test it against filing practice. Confidence returned high both
  times. This is the primary evidence for mandatory human review.

- config/check_types.yml requires the sign rationale to address
  whether zero is valid. propose_v2.md does not ask for it. The
  proposal did not address it. Prompt and config disagree.

- propose.py writes target: int_num_in_scope.value on every
  proposal regardless of check type. Wrong for unique, which
  targets a column combination, and for identity and additivity.

- Proposals rejected at review are deleted, leaving no record of what
  was rejected or why. Three were deleted in this session: two
  duplicates and one uom check asserting USD alone. rules/rejected/
  holds validation failures only, not review decisions. The review
  judgment survives in the PR discussion and nowhere in the repo.
  Decide whether rejected proposals are retained with a disposition.

- Validation rejects columns absent from the target schema but does
  not reject checks on columns marked constant. target_schema.yml
  marks segments, is_us_gaap and is_consolidated as constant; a check
  on any of them cannot fail. The prompt tells the model not to
  propose one, but nothing enforces it. Add to validate() if a
  vacuous proposal appears in the volume run.