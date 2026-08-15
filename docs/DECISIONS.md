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

