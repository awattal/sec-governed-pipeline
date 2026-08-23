# Decisions

Dated decisions with reasoning. Entries are history — superseded
decisions stay, marked as superseded.

---

## 11 Aug 2026 — Halt only on technical fault

A pipeline stops only when it physically cannot proceed. Everything
else is a finding: recorded, quantified, assigned to a domain owner,
published without stopping the run.

Reasoning: blocking data release on a quality failure stops further
issue discovery, which is the opposite of what governance is for.

## 11 Aug 2026 — Severity model dropped

Supersedes the S1/S2/S3 declared-severity scheme in docs/severity.md.

Severity was originally proposed with fault class and blast radius as
inputs. This was wrong on two counts: it conflated consequence of the
defect with confidence in the rule, and it used population scale as a
severity input rather than as a recorded metric.

Confidence belongs in rule state, not severity. Population impacted is
recorded as an attribute of the finding. Static severity labels are
dropped entirely.

## 11 Aug 2026 — CDE as the ownership anchor

Routing is by critical data element and data domain, not by severity
tier. A finding carries rule ID, data element, CDE flag, domain,
population impacted, in-scope impact, percentage in-scope impact, and
implication text.

## 11 Aug 2026 — Rate definition

Rate is rows failed divided by rows evaluated. The denominator is
stated explicitly in every metric definition.

## 11 Aug 2026 — Rule confidence is rule status, not severity

Confidence in a rule is expressed as its state in the rule registry:
proposed, accepted, retired. It is explicitly not a severity input
and not an attribute of a finding.

---

## 15 Aug 2026 — Positioning: the artifact is the routing system

The deliverable is not a set of data quality rules. It is a system
that generates candidate controls, attaches reasoning and implication,
routes them to whoever owns the judgement, and records the disposition.

Technical and financial competency are pluggable roles filled by
domain reviewers. The author's role is governance and systems design:
defining what the system can assert, how findings are routed, and how
decisions are recorded.

Consequence: the LLM is load-bearing rather than decorative. If the
author is not writing rules, generation must scale.

## 15 Aug 2026 — Check-type vocabulary fixed at nine types

Technical: not_null, unique, accepted_values, format, range,
relationship.
Financial: identity, sign, additivity.

The agent selects a type and fills its parameters. It cannot emit
free-form SQL.

Reasoning: a closed output space is what makes proposals diffable,
reviewable at a glance, and comparable across runs. An open space
reduces governance to code review, which degrades with volume.

Types 1-6 could largely be proposed by a deterministic profiler. They
are retained for coverage. Types 7-9 require reading meaning to bind
correctly and are the justification for using a language model at all.

## 15 Aug 2026 — Agent does not modify data

Profiling is read-only. The agent never cleans, corrects or drops
rows. Remediation proposals route to quarantine or exception with
human disposition.

Reasoning: cleaning destroys the distinction between what the source
reported and what the system decided it should have reported. The
flags-not-filters staging design and the provenance column exist to
preserve that line.

## 15 Aug 2026 — Rules are proposed from meaning, not distribution

Rule proposals derive from the tag definition text and the key
structure. The data profile is supplied as context only.

Reasoning: a rule derived from observed distribution encodes the
current defect rate as the standard. If 30% of a column is wrong, a
profile-derived rule permits 30% wrong and reports green. A quality
score produced by rules derived from the data they score is invalid.

## 15 Aug 2026 — Holdout evaluation across quarters

Rules proposed from 2025Q4 are evaluated against 2025Q3. A rule that
holds only on the quarter it was proposed from is overfitted to that
quarter.

Uses the multi-quarter ingest already planned. Loader is parameterised
by quarter, so cost is near zero.

## 15 Aug 2026 — Four disposition states

Supersedes the earlier two-state (recurring / one-off) model.

  wrong                     Concept or method is incorrect. Governance
                            edits or retires the rule. Not a data issue.

  remediating               Correct and being fixed. Recurring; stays
                            visible until resolved.

  accepted-with-baseline    Correct and accepted as a known fact. Count
                            at acceptance is stored. Reports zero while
                            the count stays at or below baseline.
                            Reopens if it exceeds baseline.

  ignored                   Logic and execution correct but the finding
                            is not useful. Suppressed permanently.

The rate of `wrong` dispositions is the precision metric for agent
proposals.

## 15 Aug 2026 — Thresholds set at promotion, by the reviewer

No automatic thresholds. On first observation every finding is shown
with its reasoning and implication.

A tolerance is attached only when a reviewer promotes a rule to
recurring, and is set by that reviewer. Tolerances are never derived
from the profile and never set by the agent.

Reasoning: showing everything is correct for first review and wrong
for the fiftieth run of the same known issue.

## 15 Aug 2026 — Rules are versioned

Governance may edit a rule after review. Rule ID and version are both
recorded on every finding so cross-run comparison stays valid across
an edit.

## 15 Aug 2026 — Accepted findings carry a review-by date

Prevents acceptance becoming permanent silent suppression.

## 15 Aug 2026 — Reviewer is the author

This is a solo build. There is no domain review function. The author
occupies the reviewer seat, drawing on regulated financial reporting
background. The system is built to route to a domain owner; in this
repository that owner is the author.

Stated plainly in the README rather than implied otherwise.

## 15 Aug 2026 — Dataset stays SEC-specific

Portability of the design is asserted in the README, not demonstrated
by generalising the pipeline.

Reasoning: domain knowledge of filers, tags and consolidation is why
the rules are any good. Genericising removes it and costs weeks.

## 15 Aug 2026 — Sequencing: loop before registry

Element registry and per-run history detail are deferred until a
minimal agent loop runs end to end.

Reasoning: their required fields are not knowable until agent output
exists. Earlier plan had these as blockers on the loop, which was
backwards.

Also corrected: implication text is drafted by the agent and verified
by the reviewer, not authored by hand per rule. It was previously
filed as a blocking authoring task. It is not a blocker.

## 15 Aug 2026 — Restatement is not a check type

Considered as a candidate business rule alongside accounting
identity, sign convention and quarterly additivity. Rejected.

Restatement is normal filing behaviour, not a defect. A rule
asserting against it would fire on correct data.

It remains relevant as a property of the population: the same fact
may appear with different values across filings. That is handled by
the key definition and the point-in-time versus current-view mart
decision, not by a check type.

## 15 Aug 2026 — Rules in git, findings in DuckDB

Rules, their versions and their dispositions are stored as YAML
files under version control. Findings are stored in DuckDB.

Reasoning: data/sec.duckdb is built locally and not committed, so
anything held only in the database is lost on clone. Findings are
measurement and can be regenerated by re-running the tests.
Dispositions are judgement, cannot be regenerated, and must survive.

The split follows the existing measurement/judgement separation.
It also removes the need for a rule version table and a rule
history table — git provides both. Rule lifecycle is git log.

Findings carry rule_version (git short sha) as the join back to
the rule text that produced them.

## 16 Aug 2026 — Local open-weight model comparison not built

Considered running the same prompt and vocabulary against a local
open-weight model (Llama / Nemotron / Qwen class) via Ollama and
comparing schema-violation rate, acceptance rate and cost per rule.

Not built. Available hardware is 16GB unified memory, which caps
the local model at roughly 7-14B parameters quantized. At that
size the expected result is known in advance: shallower semantic
inference and a higher rate of vocabulary violations. Building it
would consume sprint time to confirm a predictable outcome.

Recorded because the tradeoff is real and applies to institutions
that cannot call an external API: data residency, vendor risk, and
long-term reproducibility all favour local weights. An API model
version can be deprecated, leaving rule_version provenance pointing
at an uncallable model. A pinned weights file does not have this
failure mode. This is a stated weakness of the chosen path.

Mitigation: all model calls route through a single call_model
function with provider and model name in configuration, so the
swap remains cheap if it is ever needed.

## 17 Aug 2026 — API model for the first loop, provider kept swappable

Proposals are generated via the Anthropic API (`claude-sonnet-5`). All
model calls route through a single `call_model` function; provider,
endpoint and model name are configuration, not code.

Reasoning: the proposal task depends on semantic inference from
free-text definitions, where frontier models materially outperform
laptop-scale open-weight models. Cost is negligible — measured at
roughly $0.005 per proposal.

Counter-argument recorded: local open-weight models are stronger on
data residency, vendor risk and long-term reproducibility. An API
model version can be deprecated, leaving `rule_version` provenance
pointing at an uncallable model. A pinned local weights file does not
have this failure mode. This is a stated weakness of the chosen path.

## 17 Aug 2026 — Local open-weight comparison not built

Considered running the same prompt and vocabulary against a local
open-weight model via Ollama, comparing schema-violation rate,
acceptance rate and cost per rule.

Not built. Available hardware is 16GB unified memory, capping the
local model at roughly 7-14B parameters quantized. At that size the
expected result is known in advance: shallower semantic inference and
a higher rate of vocabulary violations. Building it would consume
sprint time to confirm a predictable outcome.

Recorded because the tradeoff is real and applies to institutions that
cannot call an external API. Mitigation is the `call_model`
abstraction, which keeps the swap cheap.

## 17 Aug 2026 — Rules are proposed in families, constrained on two axes

A concept may carry multiple checks, capped at five per proposal run.
One rule per concept was an unexamined default and misrepresents how
controls work: a data element carries a family of checks, not one.

Every check declares a DAMA dimension from a fixed set of six
(completeness, uniqueness, timeliness, validity, accuracy,
consistency) alongside its check type from the fixed set of nine. Both
are enforced in code; anything outside either set is rejected.

`check_type` is how the check is implemented. `dimension` is which
quality property it protects. They are separate axes and dimension
coverage cannot be derived from check types alone.

`rule_id` gains an ordinal suffix on collision within a batch.
Ordinals are unstable across regeneration; accepted because `rule_id`
only needs stability once promoted to `rules/active/`, which is the
identifier findings join on. Proposed files are drafts.

## 17 Aug 2026 — CDE designation applies to columns, not concept values

CDEs are data elements — columns. A us-gaap concept such as
`AccountsPayableCurrent` is a value within the `tag` column, not an
element, and is not a CDE candidate.

Concept-level checks (signage, identity, additivity on specific tags)
are business-requested controls, not system-originated ones. The
pipeline provides the mechanism and the review path; functional
ownership supplies the intent. The repo holds sample intents, labelled
illustrative.

## 17 Aug 2026 — CDE inheritance runs upward and unconditionally

Criticality is scored on model elements. If an element is designated
critical, every contributing element in its lineage is critical,
including through derivations. A defect in a contributor propagates to
the derived value, so the contributor carries the same criticality.

Raw elements are not scored. They inherit through `docs/LINEAGE.md`.

## 17 Aug 2026 — Data quality rules are built on the final layer only

Rules are defined against the final modelled layer —
`int_num_in_scope` for facts, `stg_submissions` and `stg_tag` for
context. Not against raw tables, and not duplicated across layers.

Reasoning: business rules require business meaning, which exists at
the modelled layer. A steward investigating a failure traces it back
through the lineage table to its source — that trace is the root cause
analysis, and it is the reason the lineage document exists.

Supersedes an earlier proposal to place checks by transform type
(raw for passthrough, both layers for recast, model for derived).
That would maintain two rules for one assertion and produce two
findings for one defect.

## 20 Aug 2026 — Structurally guaranteed rules are registered, not skipped

Three CDEs (is_us_gaap, is_consolidated, is_parent_only) are computed
by expressions that cannot return null, and two appear in the model's
WHERE clause. Their not_null rules cannot fail.

They are registered anyway. A consumer cannot see the transformation
and has no way to distinguish "not checked" from "checked and clean".
Absence from the registry is not evidence of control. The basis field
states that the rule is structurally guaranteed, so a reviewer knows
why it never fires.

Considered and rejected: excluding them on the grounds that a rule
which cannot fail inflates apparent coverage. That is a technical
test applied to a governance question.

## 22 Aug 2026 — The agent operates on the tag dictionary, not the pipeline

tag is the only column in the SEC dataset carrying free text — a label
and a definition per concept. Every other column holds codes, dates,
numbers, or identifiers, and every constraint on those is derivable
from structure. Those constraints are derived from structure.

The model is placed where meaning is written in prose and recorded
nowhere else. Anywhere else in this pipeline it would be decorative —
producing by inference what a query already produces by fact.

## 22 Aug 2026 — Generalisation claim and its precondition

The method transfers to any dataset with a data dictionary or business
glossary: the agent reads declared meaning and scales one stated intent
across every element that text describes.

It does not transfer to datasets without one. The agent reads declared
meaning; it does not infer meaning from values. Stating the precondition
is part of the claim, not a caveat attached to it.
