# AI Governance - SEC data

An AI governance case study: automated data quality rule
generation on SEC financial statement data, with human
oversight and documented evaluation.branch version

## Data

Raw SEC files are not committed to this repository - they are
large and freely available from the source. To reproduce:

1. Download [which files] from [the SEC URL]
2. Place them in `data/raw/`

## Stack
DuckDB, dbt, Dagster, GitHub Actions, Great Expectations,
LLM-assisted rule generation.

## Status
- Build local environment