# SEC Governed Pipeline

[![CI](https://github.com/awattal/sec-governed-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/awattal/sec-governed-pipeline/actions/workflows/ci.yml)

A data governance case study built on SEC financial filings. The pipeline
is real; the governed subject is an agent that proposes data quality rules
and must justify them against evidence.

Data: [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html),
2025Q4. Stack: DuckDB, dbt, Python, GitHub Actions.

**Status:** in progress. Ingest, scoping, staging models, the first
monitored rule and CI complete; the agent loop in development.

## What CI asserts

Every push and every pull request runs the pipeline on a blank machine:
install from `requirements.txt`, ingest a committed fixture, `dbt build`.
`main` accepts changes only through a pull request with that check green,
and force pushes are blocked.

The fixture is 17 whole filers from 2025Q4 — 9,735 fact rows — selected so
that tests can fail rather than pass vacuously. The composite key on `num`
is only meaningful if the data contains rows identical except on one key
column, so the fixture holds 1,036 groups differing on `segments` alone and
1,534 on `qtrs`. F10 is present at 4 rows, keeping the num-to-tag join
reachable.

**A green tick asserts correctness, not scale.** It proves the models
compile and no assertion fails on those 17 filers. It proves nothing about
behaviour at 3.8 million rows. A periodic full-volume run is open in the
backlog.

`scripts/make_fixture.py` rebuilds the fixture and profiles its own output
against every branch a test depends on, naming any that are uncovered. Two
cannot be covered by any selection because the values are absent from the
source: `abstract = 1` across all 84,907 tag rows (F26), and any group
differing on `coreg` alone (F25).

## Quickstart

Requires Python 3.12.

```bash
git clone https://github.com/awattal/sec-governed-pipeline.git
cd sec-governed-pipeline
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd transform && dbt deps && cd ..
```

Then build the database against the committed fixture:

```bash
SEC_DB_PATH=/tmp/sec_fixture.duckdb python scripts/ingest.py 2025q4 tests/fixtures/2025q4
cd transform
SEC_DB_PATH=/tmp/sec_fixture.duckdb dbt build --target ci
```

That runs the whole pipeline without downloading anything. For the full
quarter, and for the DuckDB locking constraint that will otherwise stop
you, see [`docs/setup.md`](docs/setup.md).

## Running the pipeline

From `transform/`, with the VS Code DuckDB extension disconnected:

```bash
dbt build
```

Four models build: three staging models 1:1 with source, and
`int_num_in_scope`, which applies the scope filter. 37 tests run; one warns
by design.

For monitored rules, `dbt test` reports a raw count and nothing else. The
judgement lives outside dbt:

```bash
python scripts/run_dbt_test.py f10_duration_reported_as_instant
```

```
WITHIN f10_duration_reported_as_instant 3,425 of 1,393,562 = 0.246% (tolerance 0.5%)
```

Tolerances are held as rates in `config/monitors.yml`. A dbt test measures;
whether the measurement is acceptable is a governance decision applied
separately. A threshold written into a test as a row count is calibrated to
the volume it was written at and drifts silently as that volume changes.

CI does not set `--warn-error`. F10 warns on the fixture and the build
stays green, which preserves that separation rather than collapsing it.

## Scope

Two decisions constrain the modelled layer. Both are measured, not assumed.

**us-gaap taxonomy only** (`version like 'us-gaap/%'`) — 89.9% of fact
rows, and 98.2% of rows using a standard taxonomy. Custom extension tags
are company-specific and not comparable across filers; IFRS and three
minor taxonomies account for the remainder. See F13 and F19.

**Consolidated facts only** (`segments is null`) — 41.15% of rows retained.
Segment-level rows repeat the same tag at different reporting dimensions
and would break the grain of the mart. See F14.

The scope filter is applied once, in `int_num_in_scope`. Staging models
stay 1:1 with source, carrying scope as flag columns rather than filtering
on them, so excluded rows remain in the pipeline and remain testable. F22
measures why this matters: the consolidated filter removes 60% of rows and
85% of known violations, so the defect concentrates in the rows a filtering
staging layer would have discarded.

Applying the filter is not the same as enforcing it. Until F24 the model
carried one test — the composite key — which includes `segments` and
`version`, so out-of-scope rows would have stayed mutually unique and their
arrival undetectable. The `where` clause could have been deleted with every
test green. Two assertions now hold each scope axis.

Mart columns are selected from measured coverage rather than intuition.
`Revenues`, for example, appears in only 32.5% of filings.

## Findings

[`analysis/FINDINGS.md`](analysis/FINDINGS.md) records what profiling and
scoping established. Each finding is tagged:

- **Discovery** — established once, informed a decision, does not recur.
- **Assertion** — must hold on every refresh. Implemented as a dbt test;
  a violation fails the build.
- **Monitor** — tracked with a threshold. Movement is reported, not fatal.

Two worth reading first: **F22**, which measures how the scope decision
affects the defect rate and settles the staging design on evidence, and
**F23**, where a test reporting 50 failures turned out to be one filing —
a count alone pointing at the wrong conclusion.

All findings were measured on 2025Q4.

## Layout

```
.github/ the CI workflow
analysis/ profiling and scoping SQL; FINDINGS.md
config/ monitor tolerances
data/ sec.duckdb and raw source files, both gitignored
docs/ setup.md, BACKLOG.md
scripts/ ingest, fixture builder, and the dbt bridge used by the agent
tests/ the CI fixture
transform/ the dbt project
```

## Documentation

- [`docs/setup.md`](docs/setup.md) — environment, ingesting a quarter, and
  the DuckDB single-writer constraint
- [`analysis/FINDINGS.md`](analysis/FINDINGS.md) — F1–F26
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — open work