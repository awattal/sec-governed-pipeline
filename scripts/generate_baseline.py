"""Generate baseline data quality rules from the CDE designation.

These rules follow from structure: mandatory critical elements get a
not_null check, declared grains get a unique check, and critical join
columns get a relationship check. No language model is involved -
nothing here requires reading a definition or inferring meaning.

The boundary matters. Rules derivable from structure are derived.
Rules requiring semantic inference from free-text definitions are
proposed by the model in scripts/propose.py and reviewed by a human.

rule_id carries the use case that produced the rule, so a later use
case proposing a different check on the same element does not collide.

Input:  config/cde.yml
Output: rules/active/*.yml

Usage:
    python scripts/generate_baseline.py
    python scripts/generate_baseline.py --dry-run
"""

import argparse
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "config" / "cde.yml"
ACTIVE_DIR = REPO_ROOT / "rules" / "active"

ORIGIN = "cde_assessment"


def slug(use_case: str) -> str:
    """UC-1 -> uc1. Used as the rule_id prefix."""
    return use_case.lower().replace("-", "")


def base(rule_id: str, use_case: str, today: str) -> dict:
    """Fields common to every baseline rule.

    tolerance is null deliberately: tolerances are set by a human at
    rule promotion, never derived from a measurement.

    filter is null deliberately: baseline rules apply to every row in
    the target model. Use-case rules restricting to a subset populate
    it.
    """
    return {
        "rule_id": rule_id,
        "status": "active",
        "origin": ORIGIN,
        "use_case": use_case,
        "filter": None,
        "tolerance": None,
        "created_at": today,
    }


def build_not_null(config: dict, today: str) -> list[dict]:
    """One rule per mandatory critical element."""
    uc, prefix = config["use_case"], slug(config["use_case"])
    rules = []

    for entry in config["elements"]:
        if not entry.get("mandatory"):
            continue

        model, element = entry["model"], entry["element"]
        rule = base(f"{prefix}__{model}__{element}__not_null", uc, today)
        rule.update(
            {
                "check_type": "not_null",
                "dimension": "completeness",
                "target": f"{model}.{element}",
                "assertion": {},
                "basis": entry["basis"],
                "implication": entry["implication"],
            }
        )
        rules.append(rule)
    return rules


def build_unique(config: dict, today: str) -> list[dict]:
    """One rule per declared grain."""
    uc, prefix = config["use_case"], slug(config["use_case"])
    rules = []

    for entry in config["grains"]:
        model = entry["model"]
        rule = base(f"{prefix}__{model}__grain__unique", uc, today)
        rule.update(
            {
                "check_type": "unique",
                "dimension": "uniqueness",
                "target": model,
                "assertion": {"columns": entry["columns"]},
                "basis": entry["basis"],
                "implication": entry["implication"],
            }
        )
        rules.append(rule)
    return rules


def build_relationship(config: dict, today: str) -> list[dict]:
    """One rule per declared foreign key between critical elements."""
    uc, prefix = config["use_case"], slug(config["use_case"])
    rules = []

    for entry in config["relationships"]:
        model = entry["model"]
        target_model = entry["references_model"]
        joined = "_".join(entry["columns"])

        rule = base(
            f"{prefix}__{model}__{joined}__relationship__{target_model}",
            uc,
            today,
        )
        rule.update(
            {
                "check_type": "relationship",
                "dimension": "consistency",
                "target": f"{model}.{joined}",
                "assertion": {
                    "columns": entry["columns"],
                    "references_model": target_model,
                    "references_columns": entry["references_columns"],
                },
                "basis": entry["basis"],
                "implication": entry["implication"],
            }
        )
        rules.append(rule)
    return rules


def write_rule(payload: dict, dry_run: bool) -> str:
    name = f"{payload['rule_id']}.yml"
    if dry_run:
        return name

    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    with (ACTIVE_DIR / name).open("w") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    return name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the rules that would be written, write nothing",
    )
    args = parser.parse_args()

    if not CONFIG_FILE.exists():
        raise SystemExit(f"Designation not found: {CONFIG_FILE}")

    config = yaml.safe_load(CONFIG_FILE.read_text())
    today = date.today().isoformat()

    rules = (
        build_not_null(config, today)
        + build_unique(config, today)
        + build_relationship(config, today)
    )

    for rule in rules:
        print(f"  {rule['check_type']:<13} {write_rule(rule, args.dry_run)}")

    verb = "would write" if args.dry_run else "wrote"
    print(f"\n{verb} {len(rules)} baseline rules to rules/active/")


if __name__ == "__main__":
    main()