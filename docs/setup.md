# Setup

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

1. Download a quarterly zip from the
   [SEC](https://www.sec.gov/dera/data/financial-statement-data-sets.html).
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

### Building against the fixture instead

`tests/fixtures/2025q4/` holds 17 filers in the same tab-delimited format,
committed to the repo. Ingesting them needs no download:

```bash
SEC_DB_PATH=/tmp/sec_fixture.duckdb python scripts/ingest.py 2025q4 tests/fixtures/2025q4
```

`SEC_DB_PATH` matters here. The fixture rows carry `quarter = '2025q4'`,
the same value as the real data, and `ingest.py` replaces a quarter's rows
on load. Without the override, ingesting the fixture would delete the full
quarter from `data/sec.duckdb` and leave 9,735 rows in its place.

`SEC_DB_PATH` is read by both `ingest.py` and `profiles.yml`, so one
variable steers the script and dbt at once. This is what CI sets.

To rebuild the fixture from a full quarter — after changing the filer list
in the script, or on a new quarter:

```bash
python scripts/make_fixture.py 2025q4
```

It writes the four files and prints a coverage profile naming any branch a
test depends on that the selection failed to cover.

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

## Profiles

`transform/profiles.yml` is version-controlled and holds two targets:

- `dev` — defaults to `../data/sec.duckdb`, the full quarter
- `ci` — defaults to `../data/ci.duckdb`, built fresh on each run

Both read `SEC_DB_PATH` and fall back to their default when it is unset, so
the repo needs no machine-local configuration.

DuckDB is a local file, so nothing in this profile is secret. If an adapter
requiring credentials is added, the secret goes in an environment variable
and the profile references it — never the value itself.
