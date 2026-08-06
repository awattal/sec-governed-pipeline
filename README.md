# SEC Governed Pipeline

A data governance case study built on SEC financial filings. The pipeline
is real; the governed subject is an agent that proposes data quality rules
and must justify them against evidence.

Data: [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html),
2025Q4. Stack: DuckDB, dbt, Python, GitHub Actions.

**Status:** in progress. Raw ingest and data scoping complete; dbt models
and the agent loop in development.

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/awattal/sec-governed-pipeline.git
cd sec-governed-pipeline
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

DuckDB permits a single writer. This repo ships a read-only editor
connection in `.vscode/settings.json`:

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

Read-only is deliberate, not a workaround. Every write to this database
comes from a script in version control — `scripts/ingest.py` today, dbt
models next. Undocumented manual mutation is the failure mode this project
exists to argue against.

Because `sec` is the default database, queries in `analysis/` reference
tables unqualified (`sub`, `num`) rather than `sec.sub`.

## Scope

Two decisions constrain the modelled layer. Both are measured, not assumed.

**us-gaap taxonomy only** (`version like 'us-gaap/%'`) — 98.18% of facts.
Custom extension taxonomies are company-specific and not comparable across
filers. See F13.

**Consolidated facts only** (`segments is null`) — 41.15% of rows.
Segment-level rows repeat the same tag at different reporting dimensions
and would break the grain of the mart. See F14.

Mart columns are selected from measured coverage rather than intuition.
`Revenues`, for example, appears in only 32.5% of filings.

## Findings

[`analysis/FINDINGS.md`](analysis/FINDINGS.md) records what profiling and
scoping established. Each finding is tagged:

- **Discovery** — established once, informed a decision, does not recur.
- **Assertion** — must hold on every refresh. Implemented as a dbt test;
  a violation fails the build.
- **Monitor** — tracked with a threshold. Movement is reported, not fatal.

All findings were measured on 2025Q4.

## Layout

```
analysis/    exploration, profiling and scoping SQL; FINDINGS.md
data/raw/    source files, gitignored
data/        sec.duckdb, gitignored
scripts/     ingest and operational scripts
```