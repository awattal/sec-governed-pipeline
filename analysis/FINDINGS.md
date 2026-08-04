# Findings: SEC Financial Statement Data Sets

Batch: 2025Q4
Loaded: 5 August 2026
Documented behaviour sourced from `readme.htm`, shipped inside the
quarterly ZIP.

All row counts reconciled against the source files on load:
sub 6,304 / num 3,832,977 / pre 719,346 / tag 84,907.

---

## F1: Date fields are stored and read as integers

**Documented:** `period`, `filed` and `changed` are DATE (yyyymmdd).

**Actual:** Stored as integers in the source file. DuckDB infers
BIGINT on read.

**Impact:** Date arithmetic silently produces wrong answers. The
filing lag `filed - period` for a 31 December period filed on
5 November evaluates to 10,874 rather than a number of days.
Nothing errors; the result is simply meaningless. Any downstream
model computing timeliness on these columns is wrong without
warning.

**Proposed rule:** Cast to DATE in the staging layer and fail the
load if any value cannot be cast. The type should be enforced at
the boundary rather than assumed downstream.

---

## F2: Boolean flags conform to their documented domain

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
taxonomy