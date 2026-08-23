"""Propose data quality checks for one us-gaap tag.

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
PROMPT_FILE = Path("prompts/propose_v2.md")
MAX_TOKENS = 4096

REPO_ROOT = Path(__file__).resolve().parent.parent
PROPOSED_DIR = REPO_ROOT / "rules" / "proposed"
REJECTED_DIR = REPO_ROOT / "rules" / "rejected"
DECLINED_DIR = REPO_ROOT / "rules" / "declined"
ACTIVE_DIR = REPO_ROOT / "rules" / "active"
SCHEMA_FILE = REPO_ROOT / "config" / "target_schema.yml"

TARGET_MODEL = "int_num_in_scope"

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

REQUIRED_FIELDS = {"check_type", "dimension", "assertion",
                   "rationale", "implication", "confidence"}

DIMENSIONS = {
    "completeness",
    "uniqueness",
    "timeliness",
    "validity",
    "accuracy",
    "consistency",
}

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
        f"The check will run against the {TARGET_MODEL} model, "
        f"filtered to rows where tag = '{t['tag']}'. Name the column "
        f"the check applies to in the assertion.\n"
    )


# --- Model ------------------------------------------------------------

def load_schema() -> str:
    """Return the target schema as text for the prompt.

    Injected verbatim rather than reformatted. The file is written to
    be read by a model, and a second rendering would be a second place
    the description could drift.
    """
    if not SCHEMA_FILE.exists():
        sys.exit(f"Schema file not found: {SCHEMA_FILE}")
    return SCHEMA_FILE.read_text()


def load_coverage() -> str:
    """Summarise the rules already active, one line each.

    The model cannot see the repository. Without this it re-proposes
    controls that already exist — confirmed on the first v2 run, where
    a not_null proposal duplicated both a hand-written dbt test and a
    baseline rule.

    Summarised rather than injected whole: what matters is which
    element is already checked and how, not the full rule record.
    """
    if not ACTIVE_DIR.exists():
        return "No rules are currently active."

    lines = []
    for path in sorted(ACTIVE_DIR.glob("*.yml")):
        rule = yaml.safe_load(path.read_text()) or {}
        assertion = rule.get("assertion") or {}

        # target names the model, so the checked column comes from the
        # assertion. What the model needs to know is which column is
        # already covered, not which table.
        column = assertion.get("column")
        if not column:
            columns = assertion.get("columns")
            column = f"({', '.join(columns)})" if columns else "unknown column"

        model = rule.get("target", "unknown model")
        check = rule.get("check_type", "unknown check")
        concept = rule.get("concept")
        scope = f", scoped to {concept}" if concept else ", all rows"
        lines.append(f"- {check} on {model}.{column}{scope}")

    if not lines:
        return "No rules are currently active."

    return "\n".join(lines)


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

    # The reply may contain several blocks — a thinking block can
    # precede the answer. Select by type rather than position.
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        sys.exit("Model returned no text block.")

    return (
        "\n".join(text_blocks),
        response.usage.input_tokens,
        response.usage.output_tokens,
    )


# --- Validation -------------------------------------------------------

class Rejected(Exception):
    """Reply did not satisfy the constraint. Carries the reason."""


def schema_columns() -> set[str]:
    """Return the column names declared in the target schema.

    Used to reject assertions naming columns that do not exist. The
    first v2 run proposed a uniqueness check on entity, period and
    dimensions/axis — none of which are in the model. That was caught
    at review; at volume it should be caught here.
    """
    doc = yaml.safe_load(SCHEMA_FILE.read_text()) or {}
    columns = doc.get("columns") or {}
    return set(columns.keys())


def validate(raw: str, known_columns: set[str]) -> list[dict]:
    """Parse and check the reply. Raise Rejected with a stated reason.

    v2 returns an array of checks. Every entry must satisfy the
    constraint; one bad entry rejects the whole reply, because a
    partially valid batch cannot be reviewed as a unit.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Rejected(f"reply is not valid JSON: {exc}")

    if not isinstance(parsed, list):
        raise Rejected("reply is JSON but not an array")

    if not parsed:
        raise Rejected("reply is an empty array")

    for position, entry in enumerate(parsed):
        where = f"entry {position}"

        if not isinstance(entry, dict):
            raise Rejected(f"{where} is not an object")

        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            raise Rejected(f"{where} missing fields: {sorted(missing)}")

        check_type = entry["check_type"]
        if check_type is not None and check_type not in CHECK_TYPES:
            raise Rejected(f"{where} check_type outside vocabulary: {check_type!r}")

        dimension = entry["dimension"]
        if dimension is not None and dimension not in DIMENSIONS:
            raise Rejected(f"{where} dimension outside vocabulary: {dimension!r}")

        if (check_type is None) != (dimension is None):
            raise Rejected(f"{where} check_type and dimension must both be null or both set")

        if not isinstance(entry["assertion"], dict):
            raise Rejected(f"{where} assertion is not an object")

        # The column a check runs against lives in the assertion.
        # unique asserts across a combination and uses `columns`;
        # every other check type names a single `column`. A decline
        # carries no assertion and is skipped.
        if check_type is not None:
            assertion = entry["assertion"]

            if check_type in {"unique", "relationship"}:
                named = assertion.get("columns")
                if not isinstance(named, list) or not named:
                    raise Rejected(
                        f"{where} {check_type} requires a non-empty "
                        f"assertion.columns list"
                    )
            else:
                column = assertion.get("column")
                if not isinstance(column, str) or not column.strip():
                    raise Rejected(f"{where} assertion.column is missing or empty")
                named = [column]

            unknown = [c for c in named if c not in known_columns]
            if unknown:
                raise Rejected(
                    f"{where} assertion names columns absent from the target "
                    f"schema: {sorted(unknown)}"
                )

        for field in ("rationale", "implication"):
            if not str(entry.get(field) or "").strip():
                raise Rejected(f"{where} {field} is empty")

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
    prompt = "\n\n".join([
        PROMPT_FILE.read_text(),
        "## The table checks run against\n\n" + load_schema(),
        "## Checks already active\n\n" + load_coverage(),
        build_context(tag),
    ])

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
        results = validate(raw, schema_columns())
    except Rejected as reason:
        write_yaml(
            REJECTED_DIR / f"{tag['tag'].lower()}__{now[:10]}.yml",
            {**provenance, "rejection_reason": str(reason), "raw_reply": raw},
        )
        sys.exit(f"REJECTED: {reason}")

    # A decline arrives as a single entry with check_type null. It is
    # recorded separately from proposals — a decline is evidence the
    # constraint held, not a rule awaiting review.
    if len(results) == 1 and results[0]["check_type"] is None:
        entry = results[0]
        write_yaml(
            DECLINED_DIR / f"{tag['tag'].lower()}__declined.yml",
            {
                "rule_id": f"{tag['tag'].lower()}__declined",
                **provenance,
                "rationale": entry["rationale"],
                "observation": entry.get("observation"),
            },
        )
        print("Model declined to propose a check.")
        return

    # Two checks of the same type on one concept would collide on
    # rule_id. Suffix duplicates rather than silently overwriting.
    seen: dict[str, int] = {}

    for entry in results:
        check_type = entry["check_type"]
        base = f"{tag['tag'].lower()}__{check_type}"

        seen[base] = seen.get(base, 0) + 1
        rule_id = base if seen[base] == 1 else f"{base}_{seen[base]}"

        write_yaml(
            PROPOSED_DIR / f"{rule_id}.yml",
            {
                "rule_id": rule_id,
                "status": "proposed",
                "concept": tag["tag"],
                "check_type": check_type,
                "dimension": entry["dimension"],
                "target": TARGET_MODEL,
                # The rows a check applies to. Written by the script,
                # not asked of the model — the tag is already known,
                # and the compiler needs it as structure, not prose.
                "filter": {"column": "tag", "value": tag["tag"]},
                "assertion": entry["assertion"],
                "rationale": entry["rationale"],
                "implication": entry["implication"],
                "confidence": entry["confidence"],
                "observation": entry.get("observation"),
                "definition": tag["definition"],
                "model": MODEL,
                "prompt_version": PROMPT_FILE.name,
                "proposed_at": now,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        )

    print(f"{len(results)} proposal(s) written.")


if __name__ == "__main__":
    main()