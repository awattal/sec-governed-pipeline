"""
Run a dbt test and return its result as structured data.

Usage:
    python scripts/run_dbt_test.py not_null_stg_submissions_adsh
    python scripts/run_dbt_test.py stg_submissions

This is the bridge between Python and dbt. The agent proposes a rule,
writes it as a dbt test, and needs to know what happened when it ran —
which means invoking dbt and parsing its output rather than reading
the terminal.
"""

import duckdb
import yaml
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = PROJECT_ROOT / "transform"
RUN_RESULTS = DBT_DIR / "target" / "run_results.json"

# dbt's exit codes: 0 = all passed, 1 = something failed a test,
# 2 = dbt itself errored. 1 is an expected outcome here, not a crash.
DBT_OK = 0
DBT_TEST_FAILURE = 1

MONITORS_FILE = PROJECT_ROOT / "config" / "monitors.yml"
DUCKDB_PATH = PROJECT_ROOT / "data" / "sec.duckdb"

# Statuses where dbt actually evaluated the test. Anything else means
# no measurement was taken, and `failures` carries no information.
CONCLUSIVE_STATUSES = {"pass", "fail", "warn"}

@dataclass
class TestResult:
    """One dbt test outcome."""

    unique_id: str      # full stable id, e.g. test.transform.not_null_....a942a679a5
    name: str           # readable name, derived for display only
    status: str         # pass | fail | error | skipped
    failures: int | None  # None when the test did not run
    message: str | None # populated on failure

    @property
    def conclusive(self) -> bool:
        """
        Did this test produce a usable measurement?

        A skipped or errored test reports failures as null, which is
        the absence of information rather than zero violations. Callers
        must check this before reading `failures` (F16).
        """
        return self.status in CONCLUSIVE_STATUSES
    
    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class MonitorResult:
    """
    A judgement about a measurement.

    TestResult records what dbt reported. This records what the rule's
    configured tolerance says about it. The separation is deliberate:
    the measurement is a fact, the tolerance is a governance decision
    that can change without the measurement changing.
    """

    test_name: str
    finding: str
    violations: int
    population_rows: int
    observed_rate: float
    tolerance: float

    @property
    def within_tolerance(self) -> bool:
        return self.observed_rate <= self.tolerance

    def to_dict(self) -> dict:
        return asdict(self)


def _load_monitors() -> dict:
    """Read the monitored rules and their tolerances."""
    if not MONITORS_FILE.is_file():
        return {}
    with MONITORS_FILE.open() as f:
        return yaml.safe_load(f).get("monitors", {})


def judge(result: TestResult) -> MonitorResult | None:
    """
    Compare a test's measurement against its configured tolerance.

    Returns None if the test is not a monitored rule, or if it
    produced no usable measurement.
    """
    monitors = _load_monitors()
    config = monitors.get(result.name)

    if config is None or not result.conclusive:
        return None

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        population_rows = con.execute(
            f"select count(*) from {config['population']}"
        ).fetchone()[0]
    finally:
        con.close()

    violations = result.failures or 0
    return MonitorResult(
        test_name=result.name,
        finding=config["finding"],
        violations=violations,
        population_rows=population_rows,
        observed_rate=violations / population_rows,
        tolerance=config["rate"],
    )

def _display_name(unique_id: str) -> str:
    """
    test.transform.not_null_stg_submissions_adsh.a942a679a5
        -> not_null_stg_submissions_adsh
    test.transform.f10_duration_reported_as_instant
        -> f10_duration_reported_as_instant

    Generic tests carry a trailing hash; singular tests do not.
    """
    parts = unique_id.split(".")
    tail = parts[2:]
    if len(tail) > 1:
        tail = tail[:-1]
    return ".".join(tail)


def run_test(selector: str) -> list[TestResult]:
    """
    Run `dbt test --select <selector>` and return the parsed results.

    Raises RuntimeError if dbt itself failed, which is different from
    a test failing — that comes back as a TestResult with status 'fail'.
    """
    completed = subprocess.run(
        ["dbt", "test", "--select", selector],
        cwd=DBT_DIR,
        capture_output=True,
        text=True,
    )

    if completed.returncode not in (DBT_OK, DBT_TEST_FAILURE):
        raise RuntimeError(
            f"dbt exited {completed.returncode} for selector '{selector}'\n"
            f"{completed.stdout}\n{completed.stderr}"
        )

    if not RUN_RESULTS.is_file():
        raise RuntimeError(f"dbt wrote no results file at {RUN_RESULTS}")

    with RUN_RESULTS.open() as f:
        payload = json.load(f)

    results = []
    for node in payload["results"]:
        # models appear alongside tests in this file
        if not node["unique_id"].startswith("test."):
            continue
        results.append(
            TestResult(
                unique_id=node["unique_id"],
                name=_display_name(node["unique_id"]),
                status=node["status"],
                failures=node["failures"],
                message=node["message"],
            )
        )

    if not results:
        raise RuntimeError(f"No tests matched selector '{selector}'")

    return results


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/run_dbt_test.py <test-or-model-name>")

    for result in run_test(sys.argv[1]):
        # Check conclusiveness before reading failures (F16). A test
        # that did not run reports no violations, which is not the
        # same as reporting zero.
        if not result.conclusive:
            print(f"{'NO DATA':<9} {result.name:<45} status={result.status}")
            continue

        monitor = judge(result)

        if monitor is None:
            flag = "PASS" if result.passed else result.status.upper()
            print(f"{flag:<9} {result.name:<45} failures={result.failures}")
            continue

        # A monitored rule always warns in dbt. Its status carries no
        # information; the rate against the configured tolerance does.
        verdict = "WITHIN" if monitor.within_tolerance else "BREACH"
        print(
            f"{verdict:<9} {monitor.test_name:<45} "
            f"{monitor.violations:,} of {monitor.population_rows:,} "
            f"= {monitor.observed_rate:.3%} (tolerance {monitor.tolerance:.1%})"
        )


if __name__ == "__main__":
    main()