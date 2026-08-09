# Findings: SEC Financial Statement Data Sets

Batch: 2025Q4
Loaded: 5 August 2026
Documented behaviour sourced from `readme.htm`, shipped inside the
quarterly ZIP.

All row counts reconciled against the source files on load:
sub 6,304 / num 3,832,977 / pre 719,346 / tag 84,907.

---

## Tags

Each finding is tagged by what it becomes downstream.

- **Discovery** — established once, informed a decision, does not recur.
  Some discoveries spawn an assertion; the finding stays discovery, the
  guard derived from it is listed separately.
- **Assertion** — must hold on every load. Implemented as a dbt test.
  A violation fails the build.
- **Monitor** — tracked with a threshold. Movement is reported to an
  exception table, not fatal.

| Finding | Tag | Becomes |
|---------|-----|---------|
| F1  | Discovery | Assertion: `period_end_date` and `filed_date` not null in staging |
| F2  | Assertion | `wksi`, `prevrpt`, `detail` accept only {0, 1} |
| F3  | Discovery | — (F1's cast subsumes the corrected check) |
| F4  | Monitor   | Custom share of dictionary entries; currently 91.4% |
| F5  | Discovery | — |
| F6  | Discovery | Assertion: every `adsh` in `num` resolves to `sub` |
| F7  | Assertion | `iord` accepts only {I, D}, no nulls |
| F8  | Monitor   | `qtrs > 4` row share; currently ~0.01% |
| F9  | Discovery | — |
| F10 | Monitor   | `iord = 'D'` with `qtrs = 0`; currently 0.65% of standard-tag rows |
| F11 | Assertion | Every (`tag`, `version`) in `num` resolves to `tag` |
| F12 | Assertion | Primary key unique where `segments is null` |
| F12 | Monitor   | Full-key violations; currently ~100 rows/quarter, one filer |
| F13 | Discovery | Assertion: taxonomy family within {us-gaap, ifrs, us-gaap-ebp, srt, dei} |
| F14 | Discovery | Assertion: mart grain unique with `segments is null` |
| F14 | Monitor   | `Revenues` filing coverage; currently 32.5% |
| F15 | Discovery | — |
| F16 | Assertion | Consumers branch on status before failures |
| F17 | Assertion | Filter run_results.json by unique_id prefix |
| F18 | Discovery | — |
| F19 | Discovery | Assertion: version scope is `us-gaap/%` |
| F20 | Discovery | Assertion: `coreg` populated implies `segments` populated |
| F21 | Discovery | — |
| F22 | Monitor   | Restates F10's threshold against the modelled scope |
| F23 | Discovery | In-scope assertion: `num` key holds on int_num_in_scope |
| F24 | Discovery | Assertion: in-scope rows are us-gaap and consolidated |

Thresholds are initial values set from 2025Q4 and will be revised once a
second batch establishes normal variation.

---

## F1: Date fields are stored and read as integers

**Discovery.** Derived assertion: `period_end_date` and `filed_date` not
null after the cast in `stg_submissions`. The cast returns null on an
unparseable value rather than failing the load, so the not-null test is
the control, not the cast itself. `changed_date` is excluded — see F15.

**Documented:** `period`, `filed` and `changed` are DATE (yyyymmdd).

**Actual:** Stored as integers in the source file. DuckDB infers
BIGINT on read.

**Impact:** Date arithmetic silently produces wrong answers. The
filing lag `filed - period` for a 31 December period filed on
5 November evaluates to 10,874 rather than a number of days.
Nothing errors; the result is simply meaningless. Any downstream
model computing timeliness on these columns is wrong without
warning.

**Proposed rule:** Cast to DATE in the staging layer. Implemented in
`stg_submissions` (7 Aug). The cast returns null on an unparseable value
rather than raising, so a not-null test on `period_end_date` and
`filed_date` is the control that surfaces a failure.

**Resolved:** the same subtraction now returns filing lags of 17–55 days
against a 30 September period end.

---

## F2: Boolean flags conform to their documented domain

**Assertion.** Domain {0, 1} on all three columns.

**Documented:** `wksi`, `prevrpt` and `detail` are BOOLEAN,
expressed as 1 or 0.

**Actual:** Only 1 and 0 present across all 6,304 rows.
detail: 6,294 true / 10 false.
prevrpt: 1 true / 6,303 false.
wksi: 135 true / 6,169 false.

**Impact:** None in this batch. The type is still BIGINT, so the
domain holds by convention rather than by constraint — a future
batch could contain any integer and nothing would reject it.

**Proposed rule:** Assert the value set is exactly {0, 1} on every
load. Recorded as a passing check so that a future failure is
visible as a regression rather than discovered by accident.

---

## F3: A date validity check that was wrong

**Discovery.** No recurring check; the F1 cast supersedes it.
     Retained as the documented case for human review of generated rules.

**Check:** Verify `period` is a well-formed yyyymmdd value —
eight digits, month 1-12, day 1-31.

**Initial result:** 72 rows flagged with an invalid month.

**Investigation:** The flagged filings included Rayonier, Organon
and Broadway Financial, all with a period of 20241231 — month 12,
day 31, entirely valid. The fault was in the check. DuckDB's `/`
operator returns a double, so `20241231 / 100` evaluated to
202412.31 and the modulo returned 12.31, which failed an integer
range test. Only rows whose day component produced a fractional
remainder above the boundary were caught, which is why the failure
looked like a plausible subset rather than an obvious bug.

**Corrected result:** Using integer division (`//`), zero rows
fail on length, month or day.

**Known limitations of the corrected check:** It still does not
validate real calendar dates. 20250230 would pass all three tests.
It has also only been applied to `period`; `filed` and `changed`
remain unchecked.

**Why this is recorded:** The check was syntactically valid, ran
without error, and returned a confident count of 72 violations
against named public companies. Nothing in the output indicated a
problem. It was caught only by inspecting the flagged rows rather
than trusting the count. This is the failure mode that generated
rules are most exposed to — plausible, well-formed, and wrong on
an edge case — and it is the concrete argument for human review
being a required step in this pipeline rather than an optional
one.

---

## F4: 91% of the tag vocabulary is filer-defined

**Monitor.** Custom share of dictionary entries, currently 91.4%.
     Investigate a move beyond ±5 points.

**Documented:** `custom` indicates whether a tag comes from a
standard taxonomy (0) or was created by the filer (1).

**Actual:** 7,331 standard tags against 77,576 custom, across
6,304 submissions.

**Impact:** XBRL exists to make filings machine-comparable. Where
two filers describe the same concept under two invented names, no
automated process can reconcile them. At this ratio, comparability
holds only across the small standard core.

**Proposed rule:** Track the custom-to-standard ratio per batch as
a monitored metric rather than a pass/fail test. A rule that fails
on the presence of custom tags would fail on every batch and be
switched off within a month.

---

## F5: Custom tags are overwhelmingly single-use

 **Discovery.**

**Actual:** Of the 77,576 custom tags defined, 57,392 appear on a
primary statement — leaving 20,184 defined but never used. Of
those used, 48,500 (85%) appear in exactly one submission. Only
215 appear in more than ten. The most widely reused appears in
133.

**Impact:** This distinguishes vocabulary sprawl from legitimate
extension. If filers were extending the taxonomy to fill genuine
gaps, reuse would cluster — many filers independently reaching for
the same missing concept. Instead almost every extension is a
one-off, which points to inconsistent tagging practice rather than
an inadequate standard.

**The exception worth noting:** the 215 tags reused across more
than ten filings are the opposite case. A concept that 133
separate filers needed, and that the standard taxonomy does not
provide, is evidence of a real gap. These are the candidates for
taxonomy standardisation: concepts with demonstrated multi-filer
demand that the standard taxonomy does not currently cover.


## F6 — Filings report facts for multiple periods

**Discovery.** Derived assertion: referential integrity `num` → `sub`
     on `adsh`, and grain uniqueness on any model claiming
     one-row-per-filer-per-period.

A single filing carries facts at many period-end dates, not one. 10-Q
filings average 8.6 distinct `ddate` values (min 1, max 41); 10-K
filings average 7.7 (min 3, max 39). This is expected behaviour — SEC
filings present prior-period comparatives alongside current figures —
but it means `num` cannot be treated as one row per filing per concept.

Assessment: not a defect. A grain characteristic that must be handled
explicitly.

Implication: any model at "one row per filer per fiscal period" must
constrain `ddate`. Without it, row counts inflate roughly eightfold
with no error raised.

Secondary observation: the inner join from `num` to `sub` returned
6,304 filings, matching the `sub` row count from the W1 load
reconciliation. Every filing with facts has a submission record.

## F7 — `iord` domain verified

**Assertion.** Domain {I, D}, not null.

The `iord` column in `tag` takes exactly two values, `I` (instant) and
`D` (duration), with no nulls. Companion check to F2.

Assessment: no defect. Recorded because F10 depends on this column,
and a rule built on an unverified domain is the failure mode
documented in F5.

## F8 — `qtrs` distribution and out-of-range tail

 **Monitor.** Share of rows with `qtrs > 4`, currently ~0.01%.
     Investigate above 0.1%. Flag for review, never reject.

`qtrs` states the number of quarters a value spans; `ddate` is the
period end. Distribution across 3,832,977 fact rows:

| qtrs | rows | % |
|------|-----------|-------|
| 0    | 1,773,045 | 46.26 |
| 1    | 900,883   | 23.50 |
| 3    | 851,219   | 22.21 |
| 4    | 210,120   | 5.48  |
| 2    | 97,103    | 2.53  |
| 5–101| ~500      | ~0.01 |

The near-parity of `qtrs = 1` and `qtrs = 3` is consistent with the
batch composition: a Q3 10-Q reports both the three-month period and
the nine-month year-to-date figure, producing one row of each. Annual
values (`qtrs = 4`) are only 5.48%, consistent with 353 10-K filings
against 5,278 10-Q filings in an October–December batch.

Values above 4 extend to 101 quarters (25 years), with single-digit row
counts each.

Assessment: the main distribution is coherent. The tail is
undetermined — inception-to-date reporting by development-stage
companies is legitimate, so an out-of-range value is not
self-evidently an error.

Implication: rule candidate — flag `qtrs > 4` for review rather than
reject. Distinguishing "flag" from "reject" matters here: a rejection
rule would discard valid filings, which is the F5 failure mode applied
prospectively.

## F9 — Custom tags dominate the dictionary but not the data

 **Discovery.**

Joining `num` to `tag` on (`tag`, `version`):

| tag class | rows      | % of rows | distinct tag names |
|-----------|-----------|-----------|--------------------|
| standard  | 3,509,813 | 91.57     | 4,843              |
| custom    | 323,164   | 8.43      | 57,392             |

F3 established that 91% of dictionary entries are filer-custom. That is
a statement about metadata. Measured against reported values, custom
tags account for 8.43%. Standard tags average roughly 725 uses each;
custom tags roughly 5.6.

Note: `distinct tag names` counts tag names, not (`tag`, `version`)
pairs. Custom tag names recur across filers, so the number of distinct
pairs is higher.

Assessment: not a defect. A material difference between what metadata
profiling and data profiling report about the same quarter.

Implication: profiling a catalogue answers a different question from
profiling the data it describes, and the two can support opposite
conclusions about the same population. This finding sets the scope of
the modelled layer — restricting to standard tags excludes 92% of
dictionary entries at a cost of 8.43% of reported values.

## F10 — Duration concepts reported as instants

**Monitor.** `iord = 'D'` with `qtrs = 0`. Measured on the governed
population at 0.246% (3,425 of 1,393,562). Tolerance 0.5%, held in
`config/monitors.yml` and applied by `scripts/run_dbt_test.py` — the
dbt test measures and never judges. The figures below predate F13/F14
and describe a wider population; see F22.

Each fact's `qtrs` cross-checked against its tag's declared `iord`,
standard tags only:

| iord | fact shape          | rows      | distinct tags |
|------|---------------------|-----------|---------------|
| D    | duration (qtrs > 0) | 1,801,864 | 2,969         |
| D    | instant  (qtrs = 0) | 22,930    | 715           |
| I    | instant  (qtrs = 0) | 1,685,019 | 1,873         |
| I    | duration (qtrs > 0) | 0         | 0             |

Sums to 3,509,813, reconciling to F9. 22,930 rows (0.653%) across 715
tags report a duration concept with no duration. One-directional: no
instant-declared tag is ever reported over a duration.

**Assessment:** defect. The dictionary and the fact disagree, and the
dictionary is authoritative on whether a concept is an instant.

The asymmetry suggests a systematic cause. Hypothesis, untested:
`qtrs = 0` acts as a fallback when period context fails to resolve —
durations can collapse to it, instants have nowhere to go.

**Implication:** rule candidate, `iord = 'D'` implies `qtrs > 0`.
Derived from the dataset's own metadata rather than from an assumption
about what a concept ought to mean — the distinction F5 exists to
enforce.

**Open:** sampled violations include AUD values and several exact
zeros. Whether violations skew zero-valued is unmeasured.

**Implemented.** `transform/tests/f10_duration_reported_as_instant.sql`,
a singular test joining `int_num_in_scope` to `stg_tag`. Severity is
warn with no threshold: the test reports its count on every run and
never blocks the build. Whether that count is acceptable is decided
against the configured rate, outside dbt.

The separation is deliberate. A row-count threshold written into a
test is calibrated to the volume it was written at and drifts
silently as volume changes — the failure F22 documents, in a
different form. A rate held in configuration stays meaningful.

## F11 — Referential integrity: `num` to `tag`

**Assertion.** Zero unmatched rows on the (`tag`, `version`) join.

A left join from `num` to `tag` on (`tag`, `version`) produced no
unmatched rows. Every tag referenced in the fact table resolves to a
dictionary entry.

Assessment: no defect. Recorded because it was checked, and because
the left join was chosen specifically so that unmatched rows would be
counted rather than silently dropped.

## F12 — Primary key not unique in dimensional detail

**Assertion** on the consolidated population — primary key unique
     where `segments is null`, zero exceptions.
**Monitor** on the full population — ~100 rows/quarter, routing to
     one filer. Actionable for remediation, not a build failure.

The documented primary key of `num` is (`adsh`, `tag`, `version`,
`ddate`, `qtrs`, `uom`, `segments`, `coreg`). Grouping on all eight
columns and retaining groups with more than one row:

| violation type     | key groups | affected rows |
|--------------------|------------|---------------|
| conflicting values | 49         | 98            |
| exact duplicate    | 1          | 2             |

100 rows out of 3,832,977 (0.0026%).

All 98 conflicting-value rows originate from a single filing
(`0001918712-25-000092`) and are confined to derivative disclosure
concepts: `DerivativeAssetFairValueGrossLiability`,
`DerivativeAssetNotionalAmount`, `DerivativeLiabilityNotionalAmount`.
No primary financial statement concept is affected.

Cause: the filer tags individual foreign exchange forward contracts
using a custom dimension whose members are counterparty labels
(`Canadian Imperial Bank of Commerce 1`, `Wells Fargo Bank, N.A. 2`).
Members are reused across distinct contracts, so the dimensional
context does not disambiguate the facts it is intended to separate.
The non-uniqueness reflects the filer's tagging practice and is
faithful to what was submitted.

Restricting to rows where `segments is null` — the consolidated
population — returns zero violations. The key holds without exception
on the data a financial statement mart would consume.

Assessment: defect, but concentrated and low severity. One filer, one
disclosure area, no impact on consolidated figures.

Implication: uniqueness on the full primary key is a valid rule. It
will fire approximately 100 times per quarter on this population and
route entirely to one filer, making it actionable for remediation
rather than indicative of a systemic problem. Filtering to
`segments is null` for the modelled layer is justified by the check
result, not by convenience.

Open: whether the single exact-duplicate group also originates from
that filing has not been verified.

## F13 — The dataset spans multiple taxonomies

**Discovery.** Scope decision: `version like 'us-gaap/%'`.
Derived assertion: a taxonomy family outside the known set fails the
     build, because the scope filter would otherwise drop it silently.

`custom = 0` means a tag belongs to a recognised taxonomy. It does not
mean us-gaap. Grouping standard-tag fact rows by taxonomy family:

| taxonomy    | rows      | % of rows | distinct tags |
|-------------|-----------|-----------|---------------|
| us-gaap     | 3,446,030 | 98.18     | 4,030         |
| ifrs        | 62,710    | 1.79      | 782           |
| us-gaap-ebp | 709       | 0.02      | 40            |
| srt         | 358       | 0.01      | 10            |
| dei         | 6         | 0.00      | 2             |

IFRS facts originate from foreign private issuers filing 20-F and 40-F
(97 such filings in this batch per F6). IFRS concept names do not
correspond to us-gaap concept names.

Assessment: not a defect. A population characteristic that invalidates
a common implicit assumption.

Implication: a rule suite or mart built on us-gaap concept names will
treat every IFRS filer as having missing data rather than as being out
of scope. The two are not equivalent — one is a data quality exception,
the other is a population definition. Restricting the modelled layer to
`version like 'us-gaap/%'` excludes 1.82% of standard-tag rows and
removes the need for a cross-taxonomy concept mapping layer. The
exclusion is a scoping decision, recorded here so that IFRS filers are
not later reported as defective.

## F14 — Facts exist at two levels: consolidated and dimensional

**Discovery.** Scope decision: `segments is null`.
Derived assertion: mart grain unique under that filter.
Derived monitor: `Revenues` coverage at 32.5%.

The `segments` column carries the dimensional breakdown of a value
(by business segment, equity component, counterparty, geography). Rows
where `segments` is null are consolidated totals.

| fact level  | rows      | % of rows | distinct tags |
|-------------|-----------|-----------|---------------|
| dimensional | 2,255,614 | 58.85     | 23,940        |
| consolidated| 1,577,363 | 41.15     | 54,998        |

The majority of fact rows are dimensional, not consolidated.

Headline concepts appear at both levels within the same population:

| tag                | consolidated | dimensional | filings |
|--------------------|--------------|-------------|---------|
| Assets             | 13,172       | 15,028      | 6,266   |
| Liabilities        | 11,480       | 3,894       | 5,605   |
| NetIncomeLoss      | 28,971       | 55,673      | 5,825   |
| Revenues           | 7,581        | 44,107      | 2,052   |
| StockholdersEquity | 28,805       | 123,777     | 5,691   |

Assessment: not a defect. A grain characteristic, and the one most
likely to produce a silently wrong result.

Implication: selecting a concept without constraining `segments` will
return an arbitrary row — a consolidated total or one segment's share
of it — with no error raised and no indication in the output which was
returned. Every model at company-period grain must filter
`segments is null`. This is the same class of hazard as `qtrs` (F8)
and `uom`: a constraint whose omission produces a plausible number
rather than a failure.

Secondary observation: `Revenues` appears in only 2,052 of 6,304
filings (32.5%), far below `Assets` at 6,266 (99.4%). Most filers use
more specific revenue concepts. A mart column list assembled from
intuition about which concepts "should" be present will produce sparse
columns that read as missing data.

## F15 — `changed` is null on 42% of filings

**Discovery.**

**Actual:** 2,660 of 6,304 submissions have no `changed` value. Column
types in the raw table are BIGINT for all three date columns; the nulls
are present in the source, not introduced by the staging cast — verified
by comparing null counts either side of the model.

**Assessment:** not a defect. `changed` records the date a submission was
amended. Most filings are never amended, so absence is the expected case.

**Implication:** `changed_date` cannot carry a not-null test, and a
completeness metric that counts it as a missing value will report a 42%
gap that does not exist. Recorded so this is not later raised as a data
quality exception.

Findings F1–F15 concern the SEC data. F16 onward concern the tooling —
recorded because a control is only as trustworthy as the mechanism that
reports it, and the same class of silent failure appears in both.

## F16 — An errored test reports zero failures

**Observed:** With `profiles.yml` removed, `dbt test` cannot connect to
the database. The test does not execute. `run_results.json` records
`status: error` and `failures: 0`, and the parser reports
`ERROR not_null_stg_submissions_adsh failures=0`.

**Impact:** A caller branching on the failure count alone cannot
distinguish "the rule ran and found nothing wrong" from "the rule never
ran." Both present as zero. An agent judging rule quality on failure
counts would conclude the data is clean on the basis of a test that
never touched it.

**Why this is recorded:** This is F3 in a different layer. The output is
well-formed, no exception is raised, and the number is plausible. The
only signal is a status field that a count-based check does not read.

**Assertion.** Any consumer of test results must branch on `status`
before `failures`. Only `pass` and `fail` are conclusive; `error` and
`skipped` mean the question was not answered. To be enforced by a
`conclusive` property on `TestResult` rather than by convention at each
call site.

## F17 — `run_results.json` contents depend on the invoking command

**Observed:** `dbt build` writes both model and test nodes to
`run_results.json`. `dbt test` writes test nodes only. The file is
overwritten on each invocation.

**Impact:** Model and test nodes use different status vocabularies —
`success` against `pass` — and models carry `failures: null`. A parser
that assumes a single node type produces wrong results depending on
which command last ran, with no error.

**Assertion.** Filter on `unique_id` prefix before parsing. Implemented
in `scripts/run_dbt_test.py`.

## F18 — `accepted_values` compares across types

**Observed:** The `accepted_values` test on `wksi`, `prevrpt` and
`detail` compiles to `where value_field not in ('0','1')` — quoted
string literals against BIGINT columns. The test passes because DuckDB
coerces implicitly.

**Assessment:** Correct here, fragile as a pattern. The generated SQL
does not reflect the column's actual type, and behaviour depends on the
adapter's coercion rules rather than on anything declared.

**Discovery.** Relevant when the agent generates tests: a rule that
passes may be passing for reasons unrelated to what it appears to
assert.

## F19 — `custom = 0` and us-gaap are not the same filter

**Discovery.**

| custom | us-gaap version | rows      | distinct tags |
|--------|-----------------|-----------|---------------|
| 0      | true            | 3,446,030 | 4,030         |
| 0      | false           | 63,783    | 834           |
| 1      | false           | 323,164   | 57,392        |

The fourth cell is empty. A us-gaap version implies a standard tag;
the converse does not hold.

**Assessment:** not a defect. Two filters were carried where one is
load-bearing.

**Implication:** the scope has one vocabulary axis. Drop `custom = 0`
from the scope statement.

The filter is a string pattern, and `us-gaap-ebp` fails it on prefix
form alone. Excluding employee benefit plan filings is defensible —
but it happened by accident of matching, not by decision. A filter
that excludes a population its author never considered is the F5
failure class in reverse.

---

## F20 — `coreg` is fully subsumed by `segments`

**Discovery.**

| coreg populated | segments populated | rows      |
|-----------------|--------------------|-----------|
| yes             | yes                | 39,748    |
| no              | yes                | 2,215,866 |
| no              | no                 | 1,577,363 |

No coregistrant row lacks a segment, in 3.8M rows. The consolidated
filter already removes every one. Not documented in `readme.htm`.

**Assessment:** not a defect. A structural relationship in the source.

**Implication:** `coreg is null` adds nothing to the scope filter. But
it is observed for one quarter, not guaranteed — so it becomes a cheap
assertion rather than a discarded filter, failing loudly if a future
quarter breaks the pattern and silently widens the scope.

Coregistrant rows are 1.8% of the dimensional exclusion, so F14's
58.85% is overwhelmingly segment breakdown, not subsidiary filings.

---

## F21 — The standard non-us-gaap population is 98.3% IFRS

**Discovery.**

| taxonomy    | rows   | distinct tags |
|-------------|--------|---------------|
| ifrs        | 62,710 | 782           |
| us-gaap-ebp | 709    | 40            |
| srt         | 358    | 10            |
| dei         | 6      | 2             |

Tags sum to 834, matching F19 — no tag name spans two taxonomies.

**Assessment:** not a defect. F13's characterisation is accurate and
incomplete.

**Implication:** amend F13 to say predominantly IFRS. A scope
statement that names only its largest occupant invites the reader to
assume the rest is nothing. `us-gaap-ebp` is carried into F19.

---

## F22 — F10 is scope-dependent

**Monitor.**

| scope                     | rows      | violations | rate   |
|---------------------------|-----------|------------|--------|
| all `num` rows            | 3,832,977 | 24,814     | 0.647% |
| standard tags             | 3,509,813 | 22,930     | 0.653% |
| us-gaap only              | 3,446,030 | 22,620     | 0.656% |
| + consolidated (modelled) | 1,393,562 | 3,425      | 0.246% |

Derived: the excluded dimensional rows carry 19,195 violations across
2,052,468 rows — 0.935%, or 3.8x the modelled rate. The consolidated
filter removes 60% of rows and 85% of violations.

**Assessment:** defect, unchanged from F10. What changes is the rate,
which is a property of the population.

**Implication:** F10's 1% threshold was set against 0.653% — 1.5x
headroom. Applied unchanged to the modelled layer at 0.246%, it
becomes 4x headroom and would tolerate a quadrupling before firing.
The threshold didn't move; the ground under it did. Every monitor here
carries its population in its definition.

Second: if staging applied the scope filters rather than flagging
rows, 19,195 violations would leave the pipeline entirely. The dirtier
population would become untestable precisely because it was excluded.
This is the empirical case for flags over filters in staging.

---

## F23 — The documented key fails on 50 out-of-scope groups

**Discovery.**

`dbt_utils.unique_combination_of_columns` on the documented key
(`adsh`, `tag`, `version`, `ddate`, `qtrs`, `uom`, `coreg`,
`segments`) across all 3,832,977 rows returns 50 duplicated
combinations.

All 50 are dimensional. All 50 come from a single filing,
`0001918712-25-000092`. Every group contains exactly 2 rows carrying
2 distinct values — not redundant duplication, but two different
reported figures sharing one key.

100 rows, 0.0026% of the table. The in-scope population — us-gaap,
consolidated — is unaffected, confirming the Part 2 result rather
than contradicting it.

The colliding rows are foreign currency derivative contracts whose
`segments` strings carry a trailing instance number. Rows that
collide share that number and still differ in value, so the
disambiguation the filer applied is insufficient or a dimension is
being lost upstream. The uniform group size of exactly 2 suggests a
mechanical cause rather than scattered error. Untested; stated as a
hypothesis.

**Assessment:** defect in the source, not the pipeline. Two values on
one key means the grain is unrecoverable — aggregation double-counts,
joins fan out. The SEC's key is correct; this filing produces
dimensional rows it cannot separate.

Scoping these rows out (F14) is a population decision taken during
scoping, before this finding existed. That they are also defective is
separate. Conflating the two would imply the scope was drawn to avoid
a problem.

**Implication:** the scope filter moves into a model rather than into
test configuration. `int_num_in_scope` applies `is_us_gaap and
is_consolidated` in one place; tests attach to that model and carry no
scope condition. The key test passes there at zero violations and is
asserted — a duplicate key in the governed layer makes every
downstream figure suspect, so it stops the build.

The unscoped test was removed from `stg_num` rather than kept at warn
severity. Per F4, a control that fires on every batch is switched off
rather than acted on, and a permanent warning is the same failure one
step removed. The 50 groups remain in staging and remain queryable;
what is absent is a control over them.

Monitoring the out-of-scope population is deferred; recording is not.
Out-of-scope test results are captured in the run history from W3
onward, so that a second quarter arrives with a baseline already in
place rather than becoming the first observation. Thresholds and
drift detection follow once there is a trend to detect. Recorded in
docs/BACKLOG.md.

**Note on detection.** The test reported `Got 50 results` and nothing
else. Read alone, that count suggests a systemic key defect. The
rows show one filing. `store_failures` was enabled to diagnose this
failure and the count alone pointed at the wrong conclusion — a
worked example of why a counting test is insufficient input for an
agent deciding whether a rule or the data is at fault.

---

## F24: The scope filter was applied but not enforced

**Discovery.**
Derived assertion: is_us_gaap and is_consolidated hold
on every row of int_num_in_scope.

**Documented:** F14, F19 and F22 define the governed population as
us-gaap consolidated facts. int_num_in_scope applies it in a single
where clause and the model comment states that changing scope means
changing that clause and nothing else.

**Actual:** The model carried one test — the composite key across adsh,
tag, version, ddate, qtrs, uom, coreg, segments. That key
includes segments and version, so dimensional and non-us-gaap rows
remain mutually unique. No test referenced the model's scope. The
governed population could expand from 1,393,562 rows to the full
3,832,977 with the suite still green.

**Impact:** The scope decision was documented in three findings and in
the model itself, and was still unguarded. Documentation and enforcement
had been treated as the same thing. A suite that stays green while the
governed population is silently redefined certifies the wrong property —
it confirms the pipeline runs, not that it governs what it claims to.

**Proposed rule:** Assert both scope axes on int_num_in_scope, as
separate tests so a failure names the axis. Error severity, no
threshold — a row outside scope means the filter is gone, not that a
tolerance was exceeded.

**Resolved:** Two dbt_utils.expression_is_true tests added (9 Aug).
Both pass at zero rows. dbt test --select int_num_in_scope returns
PASS=3 WARN=1, the warn being F10 at 3,425 rows — 0.246% of the governed
population, reconciling to F22.

---


