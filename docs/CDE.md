# Critical Data Element Designation

## What the frameworks prescribe

No framework prescribes a method for selecting critical data elements.
They prescribe a method for defending the selection.

DAMA-DMBOK2 gives general characteristics of critical data — usage in
regulatory reporting, financial reporting, business policy, operations
and strategy — and states that criticality drivers differ by industry.
BCBS 239 defines critical data as data required to manage the risks a
bank faces. Both are definitions anchored to purpose. Neither supplies
a selection procedure.

What practitioners converge on is the **factor rating method**:
determine the factors, weight them, rate each element against each
factor, compute score as the sum of weight times rating, set a
threshold, and document the matrix. Banking implementations of
BCBS 239 use five weighted dimensions calibrated so that roughly
10–15% of attributes in a domain qualify — and the sources for those
weights are explicit that they are practitioner judgment, not
regulator-prescribed.

The scoring is not objective. The factors and weights are chosen. What
the matrix produces is a visible chain from stated purpose to
designation, which a reviewer can challenge at any link. That is the
whole value.

## Objective

Criticality is meaningless in the abstract. An element is critical
*to* something. This designation exists to scope data quality control:
which elements warrant a fuller rule family and which are governed
with lighter checks.

## Use case (illustrative)

**UC-1.** For a given us-gaap concept and fiscal period, report the
value each registrant filed, traceable to the filing it came from,
restricted to consolidated parent-company facts.

UC-1 is illustrative. This project builds the mechanism; functional
ownership supplies real use cases. The framework below accepts a
different or additional use case without structural change — the
factor definitions and weights stay, the ratings are re-scored.

## Population scored

41 elements: the model layer, with `int_num_in_scope` scored as the
end of the chain and `stg_num` inheriting from it. The two are
column-identical — `int_num_in_scope` is `select *` from `stg_num`
with a row filter — so scoring both would double-count every
fact-level element.

| Model | Elements scored |
|---|---|
| int_num_in_scope | 16 |
| stg_submissions | 15 |
| stg_tag | 10 |

Raw columns are not scored. They inherit — see Inheritance below.

## Factors

| Factor | Question | Weight |
|---|---|---|
| Use-case dependency | Does UC-1 break without this element? | 10 |
| Failure consequence | If the value is wrong, what breaks? | 7 |
| Lineage reach | How many models consume it? | 4 |

Use-case dependency carries the highest weight because criticality is
defined relative to use. Lineage reach carries the lowest because this
DAG is four models deep and the factor separates little; it is
retained because it is the one factor computable from the repository
rather than from judgment.

### Rating scales

**Use-case dependency**
- 0 — UC-1 does not reference it
- 1 — peripheral; UC-1 works without it
- 2 — qualifies or scopes the answer
- 3 — UC-1 cannot be answered without it

**Failure consequence**
- 0 — cosmetic
- 1 — minor; misleading but not wrong
- 2 — misroutes or misclassifies a record
- 3 — corrupts a reported value

**Lineage reach**
- 0 — consumed by no model
- 1 — one model
- 2 — two models
- 3 — three or more, including join relationships

Score = Σ(weight × rating). Maximum 63.

### Threshold

The threshold is anchored to a minimum qualifying profile, stated in
words before it is stated as a number:

> An element UC-1 cannot be answered without, whose corruption
> misroutes or misstates a record, consumed by more than one model.

That profile is use-case dependency 3, failure consequence 2, lineage
reach 2, which scores 52. **Threshold: 52.**

Anchoring to a profile rather than to a fraction of the maximum means
the threshold is challengeable on its substance: an objection has to
argue with the profile, not with an arbitrary cutoff.

## Matrix

### int_num_in_scope

| Element | UD | FC | LR | Score | CDE |
|---|---|---|---|---|---|
| adsh | 3 | 3 | 3 | 63 | yes |
| tag | 3 | 3 | 3 | 63 | yes |
| segments | 3 | 3 | 2 | 59 | yes |
| period_end_date | 3 | 3 | 2 | 59 | yes |
| qtrs | 3 | 3 | 2 | 59 | yes |
| uom | 3 | 3 | 2 | 59 | yes |
| value | 3 | 3 | 2 | 59 | yes |
| is_consolidated | 3 | 2 | 2 | 52 | yes |
| is_us_gaap | 3 | 2 | 2 | 52 | yes |
| is_parent_only | 3 | 2 | 2 | 52 | yes |
| version | 2 | 2 | 3 | 46 | by inheritance |
| coreg | 2 | 2 | 2 | 42 | by inheritance |
| ddate | 2 | 2 | 2 | 42 | by inheritance |
| taxonomy | 1 | 1 | 2 | 25 | no |
| quarter | 1 | 1 | 2 | 25 | no |
| footnote | 0 | 0 | 2 | 8 | no |

All three scope flags (`is_consolidated`, `is_us_gaap`,
`is_parent_only`) rate 3 on use-case dependency: UC-1 names all three
restrictions — us-gaap concept, consolidated, parent-company — and
cannot be answered without any of them.

### stg_submissions

| Element | UD | FC | LR | Score | CDE |
|---|---|---|---|---|---|
| adsh | 3 | 3 | 2 | 59 | yes |
| cik | 3 | 3 | 1 | 55 | yes |
| period_end_date | 3 | 3 | 1 | 55 | yes |
| registrant_name | 2 | 2 | 1 | 38 | no |
| form_type | 2 | 2 | 1 | 38 | no |
| fiscal_year | 2 | 2 | 1 | 38 | no |
| fiscal_period | 2 | 2 | 1 | 38 | no |
| prevrpt | 1 | 2 | 1 | 28 | no |
| filed_date | 1 | 1 | 1 | 21 | no |
| quarter | 1 | 1 | 1 | 21 | no |
| sic_code | 0 | 0 | 1 | 4 | no |
| business_country | 0 | 0 | 1 | 4 | no |
| changed_date | 0 | 0 | 1 | 4 | no |
| wksi | 0 | 0 | 1 | 4 | no |
| detail | 0 | 0 | 1 | 4 | no |

### stg_tag

| Element | UD | FC | LR | Score | CDE |
|---|---|---|---|---|---|
| tag | 3 | 3 | 2 | 59 | yes |
| version | 2 | 2 | 2 | 42 | no |
| period_type | 2 | 2 | 1 | 38 | no |
| balance_type | 1 | 2 | 1 | 28 | no |
| taxonomy | 1 | 1 | 1 | 21 | no |
| is_custom | 1 | 1 | 1 | 21 | no |
| is_abstract | 1 | 1 | 1 | 21 | no |
| datatype | 1 | 1 | 1 | 21 | no |
| definition | 1 | 1 | 1 | 21 | no |
| label | 1 | 0 | 1 | 14 | no |

## Result

**17 of 41 scored elements are designated critical.** 14 by score,
3 by inheritance.

Raising the threshold from 42 to 52 removed four elements by score and
returned three by inheritance — a net change of one. Every element the
higher threshold removed was a contributor to an element that stayed
above it.

The inheritance rule, not the threshold, determines the designation
set in a pipeline this narrow and this derivation-heavy. A reviewer who
assumes the threshold is doing the work has misread the mechanism.

### On the count

17 of 41 is 41% of scored elements, against a banking benchmark of
10–15%. The denominator is what differs.

That benchmark is computed over an unfiltered attribute landscape —
thousands of columns across dozens of domains, most of them
administrative. The equivalent denominator here is the 69 raw columns
as ingested, of which 13 are designated: **19%**.

The wide, low-value columns were removed at staging, not by the
threshold. 22 of 36 columns in `sub` — address, phone, EIN, former
name, instance metadata — never reached the model layer. Scoring began
on an already-scoped population, which raises the percentage without
changing what was designated.

## Inheritance

If an element is critical, every element contributing to it is
critical. A defect in a contributor propagates to the derived value,
so the contributor carries the same criticality. Raw columns are
designated by inheritance, never by score.

| Raw column | Feeds |
|---|---|
| num.adsh | int_num_in_scope.adsh |
| num.tag | int_num_in_scope.tag |
| num.version | is_us_gaap, version |
| num.coreg | is_parent_only, coreg |
| num.segments | is_consolidated, segments |
| num.ddate | period_end_date, ddate |
| num.qtrs | int_num_in_scope.qtrs |
| num.uom | int_num_in_scope.uom |
| num.value | int_num_in_scope.value |
| sub.adsh | stg_submissions.adsh |
| sub.cik | stg_submissions.cik |
| sub.period | stg_submissions.period_end_date |
| tag.tag | stg_tag.tag |

13 raw columns inherit critical status. The 13 `stg_num` columns
mapping to critical `int_num_in_scope` elements inherit likewise.

## Where rules are built

Rules are defined on the final modelled layer — `int_num_in_scope` for
facts, `stg_submissions` and `stg_tag` for context. Not on raw tables,
and not duplicated across layers.

Business rules require business meaning, which exists at the modelled
layer. When a rule fails, a steward traces the failing element back
through `docs/LINEAGE.md` to its source column and the transform
applied to it. That trace is the root cause analysis. Duplicating
checks across layers would maintain two rules for one assertion and
produce two findings for one defect.

Criticality inheritance runs upward for designation. Check placement
does not follow it.

## Where this is weak

**Two of three factors are judgment.** Only lineage reach is
computable from the repository. Use-case dependency and failure
consequence are authored ratings. This is the same weakness the
banking five-dimension model carries — its weights are practitioner
benchmarks, not derived quantities. The claim here is that the process
is documented and challengeable, not that the scores are objective.

**`stg_tag.definition` is not a CDE, and the reason is categorical.**
It is the free-text field the proposal agent reads, and the agent
produces nothing without it. But CDE designation scopes control over
data flowing through the pipeline. `definition` does not flow through
the pipeline — it flows into the design of the controls applied to it.

If `definition` is corrupt, no reported value becomes wrong. A proposed
rule becomes wrong. That failure surfaces at human review of the
proposal, which is a stronger control than any data quality check
would be, and it is already in place.

`value` corrupted reaches the consumer. `definition` corrupted reaches
a reviewer. Different failure paths need different controls, and
designating `definition` as critical would apply the wrong one.

**Join partners are designated asymmetrically.**
`int_num_in_scope.version` is critical by inheritance — it feeds
`is_us_gaap` — while `stg_tag.version` is not, despite the two being
join partners. The inheritance rule follows derivation, not
relationship. Left as-is and recorded rather than patched: extending
inheritance across joins would designate most of the model layer and
dissolve the distinction the designation exists to draw.

**A single use case scores everything.** UC-1 is one illustrative
report. A real designation exercise cross-checks elements across
several use cases, since an element peripheral to one may be central
to another. This framework accepts additional use cases without
structural change; it has not been run against any.