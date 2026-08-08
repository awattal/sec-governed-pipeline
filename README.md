# SEC Governed Pipeline

A data governance case study built on SEC financial filings. The pipeline
is real; the governed subject is an agent that proposes data quality rules
and must justify them against evidence.

Data: [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html),
2025Q4. Stack: DuckDB, dbt, Python, GitHub Actions.

**Status:** in progress. Ingest, scoping, staging models and the first
monitored rule complete; the agent loop in development.

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/awattal/sec-governed-pipeline.git
cd sec-governed-pipeline
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the dbt packages:

```bash
cd transform
dbt deps
cd ..
```

`dbt deps` reads `packages.yml` and installs `dbt_utils`, which the tests
depend on. Skipping it produces a compilation error rather than a missing
package error, which is harder to recognise.

## Building the database

The DuckDB file is not in version control — it is rebuilt from source data.

1. Download a quarterly zip from the SEC link above.
2. Extract it to `data/raw/<quarter>/`, e.g. `data/raw/2025q4/`. You should
   have four files: `sub.txt`, `num.txt`, `tag.txt`, `pre.txt`.
3. Run the ingest:

```bash
python scripts/ingest.py 2025q4
```

The script validates that all four files are present before touching the
database, loads each into a table, and prints row counts by quarter.

Re-running is safe. Each row carries a `quarter` column, and a re-run
replaces only that quarter's rows — so quarters accumulate and no load is
ever doubled.

## Working with the database

DuckDB permits a single writer, and the VS Code DuckDB extension takes an
exclusive lock on the file when connected — **including when `readOnly` is
set**. The setting does not do what its name suggests in this context.

**Disconnect the extension before any dbt run or script write.** Otherwise
the write fails with a lock error that does not name the extension as the
cause.

The repo ships an editor connection in `.vscode/settings.json`:

```jsonc
{
  "duckdb.databases": [
    {
      "alias": "sec",
      "type": "file",
      "path": "./data/sec.duckdb",
      "attached": true,
      "readOnly": true
    }
  ],
  "duckdb.defaultDatabase": "sec"
}
```

`readOnly` is kept as a statement of intent rather than an enforced
constraint: every write to this database comes from a script in version
control — `scripts/ingest.py` and dbt. Undocumented manual mutation is the
failure mode this project exists to argue against. The lock, not the
setting, is what actually prevents it.

Because `sec` is the default database, queries in `analysis/` reference
tables unqualified (`sub`, `num`) rather than `sec.sub`.

For command-line queries while the extension is attached, use the
`-readonly` flag, which does work:

```bash
duckdb -readonly data/sec.duckdb -c "select count(*) from stg_num"
```

## Running the pipeline

From `transform/`, with the VS Code extension disconnected:

```bash
dbt run     # build the models
dbt test    # run the tests
```

Four models build: three staging models 1:1 with source, and
`int_num_in_scope`, which applies the scope filter. 35 tests run; one warns
by design.

For monitored rules, `dbt test` reports a raw count and nothing else. The
judgement lives outside dbt:

```bash
python scripts/run_dbt_test.py f10_duration_reported_as_instant
```

```
WITHIN  f10_duration_reported_as_instant  3,425 of 1,393,562 = 0.246% (tolerance 0.5%)
```

Tolerances are held as rates in `config/monitors.yml`. A dbt test measures;
whether the measurement is acceptable is a governance decision applied
separately. A threshold written into a test as a row count is calibrated to
the volume it was written at and drifts silently as that volume changes.

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
analysis/    profiling and scoping SQL; FINDINGS.md
config/      monitor tolerances
data/        sec.duckdb and raw source files, both gitignored
docs/        BACKLOG.md
scripts/     ingest, and the dbt bridge used by the agent
transform/   the dbt project
```