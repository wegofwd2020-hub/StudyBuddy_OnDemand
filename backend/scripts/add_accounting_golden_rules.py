"""
backend/scripts/add_accounting_golden_rules.py

Add the three golden rules of accounting to the Introduction to Accounting
lesson's Key points (#757).

    python scripts/add_accounting_golden_rules.py                 # dry-run (default)
    python scripts/add_accounting_golden_rules.py --commit        # write
    python scripts/add_accounting_golden_rules.py --root /path    # another store

A content EDIT rather than a regeneration: the lesson is otherwise correct and
already reviewed, and regenerating would rewrite its prose (and cost a model
call) to add three sentences.

Idempotent: a lesson that already states a golden rule is left alone, so
re-running — or running after the demo run — cannot stack duplicates. Only
`key_points` is touched; every other field is written back unchanged, and the
script asserts that before writing.

After a --commit on a live store, clear the Redis `content:*` keys the way
scripts/demo/sync-content.sh step 5 does (never FLUSHDB).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from dataclasses import dataclass

# Run as `python /app/scripts/<this>.py`, sys.path[0] is the SCRIPTS directory, so
# `from config import settings` below (the default --root) raises ModuleNotFoundError.
# Caught on the demo: the unit tests always pass --root and never import config.
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

UNIT_ID = "G11-ACC-001"
LESSON_FILE = "lesson_en.json"

GOLDEN_RULES = [
    "Golden rule — Personal accounts: debit the receiver, credit the giver.",
    "Golden rule — Real accounts: debit what comes in, credit what goes out.",
    "Golden rule — Nominal accounts: debit all expenses and losses, credit all incomes and gains.",
]

_MARKER = "golden rule"


class GoldenRulesError(Exception):
    """The edit would have changed something other than `key_points`."""


@dataclass
class Report:
    files_seen: int = 0
    files_changed: int = 0
    files_already_done: int = 0


def _already_has_rules(body: dict) -> bool:
    return any(_MARKER in str(p).lower() for p in body.get("key_points") or [])


def _write_atomic(path: str, body: dict) -> None:
    tmp = f"{path}.golden.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def add_rules(root: str, *, commit: bool) -> Report:
    report = Report()
    pattern = os.path.join(root, "curricula", "*", UNIT_ID, LESSON_FILE)

    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as f:
            original = json.load(f)

        report.files_seen += 1
        if _already_has_rules(original):
            report.files_already_done += 1
            continue

        updated = dict(original)
        updated["key_points"] = [*(original.get("key_points") or []), *GOLDEN_RULES]

        # Only the key points may differ. A script that rewrites a reviewed lesson
        # in any other way is a content defect, not an edit.
        if {k: v for k, v in updated.items() if k != "key_points"} != {
            k: v for k, v in original.items() if k != "key_points"
        }:
            raise GoldenRulesError(f"would change more than key_points: {path}")

        report.files_changed += 1
        if commit:
            _write_atomic(path, updated)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add the 3 golden rules of accounting (#757)")
    parser.add_argument("--root", default=None, help="content store root")
    parser.add_argument("--commit", action="store_true", help="write (default: dry-run)")
    args = parser.parse_args(argv)

    root = args.root
    if root is None:
        from config import settings

        root = settings.CONTENT_STORE_PATH

    try:
        report = add_rules(root, commit=args.commit)
    except GoldenRulesError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2

    mode = "COMMIT" if args.commit else "DRY-RUN"
    print(f"[{mode}] root={root} unit={UNIT_ID}")
    print(
        f"  lessons seen: {report.files_seen}  to change: {report.files_changed}"
        f"  already had the rules: {report.files_already_done}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
