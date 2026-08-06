"""
Rebuild the SEC DuckDB database from raw quarterly files.

Usage:
    python scripts/ingest.py 2025q4

Loads sub, num, tag and pre for one quarter into data/sec.duckdb.
Safe to re-run: that quarter's rows are replaced, other quarters are untouched.
"""

import sys
from pathlib import Path

import duckdb

TABLES = ["sub", "num", "tag", "pre"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "sec.duckdb"


def parse_args() -> str:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/ingest.py <quarter>    e.g. 2025q4")
    return sys.argv[1].lower()


def validate(raw_dir: Path) -> None:
    if not raw_dir.is_dir():
        sys.exit(f"Folder not found: {raw_dir}")
    missing = [t for t in TABLES if not (raw_dir / f"{t}.txt").is_file()]
    if missing:
        sys.exit(f"Missing in {raw_dir}: {', '.join(m + '.txt' for m in missing)}")


def table_exists(con, table: str) -> bool:
    return con.execute(
        "select count(*) from duckdb_tables() where table_name = ?", [table]
    ).fetchone()[0] > 0


def load_table(con, table: str, path: Path, quarter: str) -> None:
    source = (
        f"select *, '{quarter}' as quarter "
        f"from read_csv('{path}', delim='\\t', header=true, sample_size=-1)"
    )
    if table_exists(con, table):
        con.execute(f"delete from {table} where quarter = ?", [quarter])
        con.execute(f"insert into {table} {source}")
    else:
        con.execute(f"create table {table} as {source}")


def report(con) -> None:
    print("\nrow counts by quarter")
    for table in TABLES:
        rows = con.execute(
            f"select quarter, count(*) from {table} group by quarter order by quarter"
        ).fetchall()
        for quarter, count in rows:
            print(f"  {table:<4} {quarter:<8} {count:>12,}")


def main() -> None:
    quarter = parse_args()
    raw_dir = PROJECT_ROOT / "data" / "raw" / quarter
    validate(raw_dir)

    con = duckdb.connect(str(DB_PATH))
    try:
        for table in TABLES:
            load_table(con, table, raw_dir / f"{table}.txt", quarter)
            print(f"loaded {table}")
        report(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()