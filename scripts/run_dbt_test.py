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


@dataclass
class TestResult:
    """One dbt test outcome."""

    unique_id: str      # full stable id, e.g. test.transform.not_null_....a942a679a5
    name: str           # readable name, derived for display only
    status: str         # pass | fail | error | skipped
    failures: int       # rows that violated the test
    message: str | None # populated on failure

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict:
        return asdict(self)


def _display_name(unique_id: str) -> str:
    """test.transform.not_null_stg_submissions_adsh.a942a679a5 -> not_null_stg_submissions_adsh"""
    parts = unique_id.split(".")
    return ".".join(parts[2:-1])


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
                failures=node["failures"] or 0,
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
        flag = "PASS" if result.passed else result.status.upper()
        print(f"{flag:<6} {result.name:<45} failures={result.failures}")


if __name__ == "__main__":
    main()