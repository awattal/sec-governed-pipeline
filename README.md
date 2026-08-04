# AI Governance - SEC Data Quality

An AI governance case study: automated data quality rule generation
on SEC financial statement data, with human oversight and documented
evaluation.

## Data

Source: SEC Financial Statement Data Sets, quarterly bulk XBRL
extracts from corporate filings.
https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets

Current batch: 2025Q4 (four tab-separated files)

| File    | Rows      | Contents                                    |
|---------|-----------|---------------------------------------------|
| sub     | 6,304     | One row per EDGAR submission                |
| num     | 3,832,977 | Numeric facts from primary statements       |
| pre     | 719,346   | Filer-assigned line item labels and order   |
| tag     | 84,907    | Tags used, standard and custom              |

Raw data is not committed - files are large and freely available
from the source.

### Reproducing

1. Download a quarterly ZIP from the SEC link above
2. Place it in `data/landing/`
3. Extract into `data/raw/<quarter>/`
4. Move the ZIP to `data/archive/`

### Directory structure

data/
  landing/    incoming ZIPs
  raw/        extracted files, partitioned by quarter
  archive/    processed ZIPs retained

- Separate folders per quarter to help identify batch and enable isloated run of each batch
- Original ZIP kept as a reference copy to enable rebuild or integrity checks

## Stack

DuckDB, dbt, Dagster, GitHub Actions, Great Expectations,
LLM-assisted rule generation.

- **DuckDB** - single-file analytical database. No server or
  credentials, so the project runs anywhere from a clone. SQL is
  close enough to Snowflake or Postgres that the models port.
- **dbt** - transformation layer. Models are version-controlled
  SQL with dependencies, tests, and generated lineage, which makes
  the pipeline reviewable rather than opaque.
- **Dagster** - orchestration. Sequences ingestion, transformation,
  and quality checks with run history and failure visibility.
- **GitHub Actions** - CI. Runs tests on every change before it
  merges, so no unvalidated transformation reaches the main branch.
- **Great Expectations** - data quality suite. Declarative
  expectations over critical data elements, with results captured
  as exceptions rather than logs.
- **LLM rule generation** - candidate DQ rules proposed from column
  metadata and profiling, evaluated against a hand-built gold set.
  Human review is a required step; no generated rule is applied
  unreviewed.

## Governance approach


## Status

- [x] Local environment and repository
- [x] 2025Q4 data acquired and staged
- [ ] DuckDB load with row count reconciliation
- [ ] dbt models, tests, lineage
- [ ] Orchestration and CI
- [ ] Data quality suite
- [ ] LLM rule generation and evaluation