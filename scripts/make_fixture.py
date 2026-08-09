"""
Build the CI fixture: a small, deliberately selected slice of a real
quarter, written in the source's own tab-delimited format.

Usage:
    python scripts/make_fixture.py 2025q4

Reads data/sec.duckdb and writes tests/fixtures/<quarter>/.
Output is committed; CI ingests it through scripts/ingest.py.

Filers are hard-coded rather than selected by rule. The fixture is
CI's input, so its contents must not change when the source data does.
Each is present for a stated reason -- see FILERS below.
"""

import sys
from pathlib import Path

import duckdb

TABLES = ["sub", "num", "tag", "pre"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "sec.duckdb"

# Selected 9 Aug 2026 against 2025Q4. Each entry states what it covers;
# removing one removes that coverage.
FILERS = {
    "0000733590-25-000029": "segments discrimination, 23 variants on one key",
    "0001193125-25-270327": "uom discrimination",
    "0001137774-25-000178": "qtrs discrimination",
    "0001628280-25-056158": "coreg populated, 17 periods, null values",
    "0001859392-25-000070": "coreg populated, 15 periods",
    "0000096223-25-000014": "coreg populated, no null values (contrast)",
    "0001683168-25-007766": "smallest viable filer, 292 rows",
    "0001104659-25-124947": "F10 reachability",
    "0001193125-25-277530": "F10 reachability",
    "0001628280-25-049531": "F10 reachability",
    "0001213900-25-119743": "ifrs taxonomy, excluded by scope",
    "0000067887-25-000138": "us-gaap-ebp, the F19 boundary case",
    "0000002488-25-000166": "changed is null (F15)",
    "0000003499-25-000026": "changed is null (F15)",
    "0001628280-25-046279": "prevrpt = 1, the only such filing in 2025Q4; also us-gaap-ebp",
    "0001437749-25-036305": "wksi = 1 (F2)",
    "0001553350-25-000108": "detail = 0 (F2)",
}


def parse_args() -> str:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/make_fixture.py <quarter>    e.g. 2025q4")
    return sys.argv[1].lower()


def adsh_list(con) -> str:
    """Register the filer list as a temp table and return its name."""
    con.execute("create or replace temp table fixture_filers (adsh varchar)")
    con.executemany(
        "insert into fixture_filers values (?)", [(a,) for a in FILERS]
    )
    found = con.execute(
        "select count(*) from sub where adsh in (select adsh from fixture_filers)"
    ).fetchone()[0]
    if found != len(FILERS):
        sys.exit(
            f"Expected {len(FILERS)} filers in sub, found {found}. "
            "The quarter loaded may not be the one the list was built against."
        )
    return "fixture_filers"


def extract(con, quarter: str, out_dir: Path) -> dict:
    """Write the four fixture files. Returns row counts."""
    counts = {}

    # sub, num, pre: whole filers.
    for table in ["sub", "num", "pre"]:
        con.execute(f"""
            create or replace temp table fx_{table} as
            select * exclude (quarter)
            from {table}
            where quarter = '{quarter}'
              and adsh in (select adsh from fixture_filers)
        """)

    # tag: only rows referenced by the fixture's num or pre rows.
    # pre matters -- abstract concepts never appear in num, so pruning
    # on num alone would leave is_abstract uniformly false.
    con.execute("""
        create or replace temp table fx_tag as
        select t.* exclude (quarter)
        from tag t
        where (t.tag, t.version) in (select tag, version from fx_num)
           or (t.tag, t.version) in (select tag, version from fx_pre)
    """)

    for table in TABLES:
        path = out_dir / f"{table}.txt"
        con.execute(f"""
            copy fx_{table} to '{path}'
            (format csv, delimiter '\t', header true)
        """)
        counts[table] = con.execute(f"select count(*) from fx_{table}").fetchone()[0]

    return counts


def profile(con) -> None:
    """Report branch coverage. Every line here maps to a test that would
    pass vacuously if the count were zero."""

    checks = [
        ("taxonomies in num",
         "select count(distinct split_part(version,'/',1)) from fx_num"),
        ("  us-gaap rows",
         "select count(*) from fx_num where split_part(version,'/',1)='us-gaap'"),
        ("  us-gaap-ebp rows (F19)",
         "select count(*) from fx_num where split_part(version,'/',1)='us-gaap-ebp'"),
        ("  ifrs rows",
         "select count(*) from fx_num where split_part(version,'/',1)='ifrs'"),
        ("  custom-taxonomy rows",
         "select count(*) from fx_num where version like '00%'"),
        ("dimensional rows (segments not null)",
         "select count(*) from fx_num where segments is not null"),
        ("consolidated rows (segments null)",
         "select count(*) from fx_num where segments is null"),
        ("coreg populated",
         "select count(*) from fx_num where coreg is not null"),
        ("null value",
         "select count(*) from fx_num where value is null"),
        ("negative value",
         "select count(*) from fx_num where value < 0"),
        ("distinct ddate",
         "select count(distinct ddate) from fx_num"),
        ("distinct uom",
         "select count(distinct uom) from fx_num"),
        ("tag: iord = I",
         "select count(*) from fx_tag where iord = 'I'"),
        ("tag: iord = D",
         "select count(*) from fx_tag where iord = 'D'"),
        ("tag: custom = 1",
         "select count(*) from fx_tag where custom = 1"),
        ("tag: custom = 0",
         "select count(*) from fx_tag where custom = 0"),
        ("tag: abstract = 1",
         "select count(*) from fx_tag where abstract = 1"),
        ("tag: abstract = 0",
         "select count(*) from fx_tag where abstract = 0"),
        ("tag: crdr null (non-monetary)",
         "select count(*) from fx_tag where crdr is null"),
        ("tag: same tag under 2+ versions",
         "select count(*) from (select tag from fx_tag group by tag having count(distinct version) > 1)"),
        ("sub: changed null (F15)",
         "select count(*) from fx_sub where changed is null"),
        ("sub: changed populated",
         "select count(*) from fx_sub where changed is not null"),
        ("sub: wksi = 1",
         "select count(*) from fx_sub where wksi = 1"),
        ("sub: prevrpt = 1",
         "select count(*) from fx_sub where prevrpt = 1"),
        ("sub: detail = 0",
         "select count(*) from fx_sub where detail = 0"),
        ("PK: groups differing on segments only",
         """select count(*) from (select adsh,tag,version,ddate,qtrs,uom from fx_num
            group by all having count(distinct segments) > 1)"""),
        ("PK: groups differing on uom only",
         """select count(*) from (select adsh,tag,version,ddate,qtrs,segments,coreg from fx_num
            group by all having count(distinct uom) > 1)"""),
        ("PK: groups differing on qtrs only",
         """select count(*) from (select adsh,tag,version,ddate,uom,segments,coreg from fx_num
            group by all having count(distinct qtrs) > 1)"""),
        ("PK: groups differing on coreg only (expect 0, see F25)",
         """select count(*) from (select adsh,tag,version,ddate,qtrs,uom,segments from fx_num
            group by all having count(distinct coreg) > 1)"""),
        ("F10: duration reported as instant, in scope",
         """select count(*) from fx_num n join fx_tag t
            on t.tag = n.tag and t.version = n.version
            where t.iord = 'D' and n.qtrs = 0 and n.segments is null
              and split_part(n.version,'/',1) = 'us-gaap'"""),
    ]

    print("\ncoverage profile")
    gaps = []
    for label, sql in checks:
        n = con.execute(sql).fetchone()[0]
        marker = " " if n > 0 else " GAP"
        if n == 0 and "expect 0" not in label:
            gaps.append(label)
        print(f"  {label:<48} {n:>8,}{marker}")

    if gaps:
        print(f"\n{len(gaps)} uncovered branch(es):")
        for g in gaps:
            print(f"  - {g}")
        print("Each is a test that would pass without being able to fail.")
    else:
        print("\nAll branches covered.")


def main() -> None:
    quarter = parse_args()
    out_dir = PROJECT_ROOT / "tests" / "fixtures" / quarter
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        adsh_list(con)
        counts = extract(con, quarter, out_dir)
        print(f"\nwrote {out_dir}")
        for table, n in counts.items():
            print(f"  {table:<4} {n:>8,}")
        profile(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()