"""Propose one data quality check for one us-gaap tag.

Reads the tag and its SEC definition from DuckDB, sends it to a model
under a fixed check-type vocabulary, validates the reply against that
vocabulary, and writes the result to rules/proposed/ as YAML.

The model may decline. Declines are recorded, not discarded.
Replies that fail validation are recorded in rules/rejected/, because
refusals are evidence that the constraint is being enforced.

Usage:
    python scripts/propose.py AccountsPayableCurrent
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml
from anthropic import Anthropic

# --- Configuration ----------------------------------------------------

MODEL = "claude-sonnet-5"
PROMPT_FILE = Path("prompts/propose_v1.md")
MAX_TOKENS = 1024

REPO_ROOT = Path(__file__).resolve().parent.parent
PROPOSED_DIR = REPO_ROOT / "rules" / "proposed"
REJECTED_DIR = REPO_ROOT / "rules" / "rejected"
DECLINED_DIR = REPO_ROOT / "rules" / "declined"

# The action space. The model may return one of these or null.
# Anything else is rejected. This constant is the governance boundary.
CHECK_TYPES = {
    "not_null",
    "unique",
    "accepted_values",
    "format",
    "range",
    "relationship",
    "identity",
    "sign",
    "additivity",
}

REQUIRED_FIELDS = {"check_type", "assertion", "rationale", "implication", "confidence"}

# Encodings are expanded to words before the model sees them. Both
# columns may use single letters, and "D" means duration in one and
# debit in the other — an ambiguity the model should never have to
# resolve. Unknown values fall through unchanged rather than being
# silently mislabelled.
PERIOD_TYPE_WORDS = {"I": "instant", "D": "duration"}
BALANCE_TYPE_WORDS = {"C": "credit", "D": "debit",
                      "credit": "credit", "debit": "debit"}


# --- Data -------------------------------------------------------------

def fetch_tag(db_path: str, tag: str) -> dict:
    """Read one standard us-gaap tag and its context from stg_tag."""
    con = duckdb.connect(db_path, read_only=True)
    try:
        row = con.execute(
            """
            select tag, version, label, definition,
                   datatype, period_type, balance_type
            from main.stg_tag
            where tag = ?
              and version like 'us-gaap/%'
            limit 1
            """,
            [tag],
        ).fetchone()
    finally:
        con.close()

    if row is None:
        sys.exit(f"Tag not found among standard us-gaap tags: {tag}")

    keys = ["tag", "version", "label", "definition",
            "datatype", "period_type", "balance_type"]
    return dict(zip(keys, row))


def build_context(t: dict) -> str:
    """Render the tag as the context block appended to the prompt."""
    period = PERIOD_TYPE_WORDS.get(t["period_type"], t["period_type"])
    balance = BALANCE_TYPE_WORDS.get(t["balance_type"], t["balance_type"])

    return (
        f"## Concept\n\n"
        f"tag: {t['tag']}\n"
        f"version: {t['version']}\n"
        f"label: {t['label']}\n"
        f"datatype: {t['datatype']}\n"
        f"period type: {period}\n"
        f"balance type: {balance}\n\n"
        f"definition:\n{t['definition']}\n\n"
        f"The check will run against int_num_in_scope.value, "
        f"filtered to rows where tag = '{t['tag']}'.\n"
    )


# --- Model ------------------------------------------------------------

def call_model(prompt: str) -> tuple[str, int, int]:
    """Send text, return (reply text, input tokens, output tokens).

    The only place in the codebase that knows which provider is used.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set in this shell.")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return (
        response.content[0].text,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )


# --- Validation -------------------------------------------------------

class Rejected(Exception):
    """Reply did not satisfy the constraint. Carries the reason."""


def validate(raw: str) -> dict:
    """Parse and check the reply. Raise Rejected with a stated reason."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Rejected(f"reply is not valid JSON: {exc}")

    if not isinstance(parsed, dict):
        raise Rejected("reply is JSON but not an object")

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        raise Rejected(f"missing required fields: {sorted(missing)}")

    check_type = parsed["check_type"]
    if check_type is not None and check_type not in CHECK_TYPES:
        raise Rejected(f"check_type outside vocabulary: {check_type!r}")

    if not isinstance(parsed["assertion"], dict):
        raise Rejected("assertion is not an object")

    for field in ("rationale", "implication"):
        if not str(parsed.get(field) or "").strip():
            raise Rejected(f"{field} is empty")

    return parsed


# --- Output -----------------------------------------------------------

def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="us-gaap tag name, e.g. AccountsPayableCurrent")
    args = parser.parse_args()

    db_path = os.environ.get("SEC_DB_PATH")
    if not db_path:
        sys.exit("SEC_DB_PATH is not set in this shell.")

    if not PROMPT_FILE.exists():
        sys.exit(f"Prompt file not found: {PROMPT_FILE}")

    tag = fetch_tag(db_path, args.tag)
    prompt = PROMPT_FILE.read_text() + "\n\n" + build_context(tag)

    raw, tokens_in, tokens_out = call_model(prompt)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    provenance = {
        "concept": tag["tag"],
        "definition": tag["definition"],
        "model": MODEL,
        "prompt_version": PROMPT_FILE.name,
        "proposed_at": now,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }

    try:
        result = validate(raw)
    except Rejected as reason:
        write_yaml(
            REJECTED_DIR / f"{tag['tag'].lower()}__{now[:10]}.yml",
            {**provenance, "rejection_reason": str(reason), "raw_reply": raw},
        )
        sys.exit(f"REJECTED: {reason}")

    check_type = result["check_type"]

    if check_type is None:
        write_yaml(
            DECLINED_DIR / f"{tag['tag'].lower()}__declined.yml",
            {
                "rule_id": f"{tag['tag'].lower()}__declined",
                **provenance,
                "rationale": result["rationale"],
                "observation": result.get("observation"),
            },
        )
        print("Model declined to propose a check.")
        return

    rule_id = f"{tag['tag'].lower()}__{check_type}"
    write_yaml(
        PROPOSED_DIR / f"{rule_id}.yml",
        {
            "rule_id": rule_id,
            "status": "proposed",
            "concept": tag["tag"],
            "check_type": check_type,
            "target": "int_num_in_scope.value",
            "assertion": result["assertion"],
            "rationale": result["rationale"],
            "implication": result["implication"],
            "confidence": result["confidence"],
            "observation": result.get("observation"),
            "definition": tag["definition"],
            "model": MODEL,
            "prompt_version": PROMPT_FILE.name,
            "proposed_at": now,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        },
    )


if __name__ == "__main__":
    main()