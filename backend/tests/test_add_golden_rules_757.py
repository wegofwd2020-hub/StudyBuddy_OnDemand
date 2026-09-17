"""
tests/test_add_golden_rules_757.py

The three golden rules of accounting belong in the Introduction to Accounting
lesson (Venki, 14 Sep — #757):

    "These rules should be added to the Key points section of the Introduction
     to Accounting lesson."

A content edit, not a regeneration: the lesson is otherwise correct and
regenerating it would rewrite prose the tester has already reviewed (and cost a
model call). The script appends three key points and touches nothing else.

Idempotent on purpose — the demo run and any later re-run must not stack six
rules, and the script is the kind of thing that gets run twice.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import add_accounting_golden_rules as script  # noqa: E402


def _lesson(root, curriculum="default-2026-g11-commerce", unit="G11-ACC-001", **over) -> str:
    body = {
        "unit_id": unit,
        "subject": "Accountancy",
        "topic": "Introduction to Accounting",
        "title": "Introduction to Accounting: The Accounting Equation",
        "sections": [{"heading": "Introduction", "body": "Accounting records transactions."}],
        "key_points": ["The accounting equation must hold after every transaction."],
        "language": "en",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
        **over,
    }
    d = os.path.join(root, "curricula", curriculum, unit)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "lesson_en.json")
    with open(path, "w") as f:
        json.dump(body, f)
    return path


def _read(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def test_dry_run_writes_nothing(tmp_path):
    path = _lesson(str(tmp_path))
    before = _read(path)

    report = script.add_rules(str(tmp_path), commit=False)

    assert _read(path) == before
    assert report.files_changed == 1


def test_commit_appends_the_three_rules(tmp_path):
    path = _lesson(str(tmp_path))

    script.add_rules(str(tmp_path), commit=True)
    after = _read(path)

    assert len(after["key_points"]) == 4
    joined = " ".join(after["key_points"]).lower()
    for phrase in [
        "debit the receiver, credit the giver",
        "debit what comes in, credit what goes out",
        "debit all expenses and losses, credit all incomes and gains",
    ]:
        assert phrase in joined, phrase
    # The original point is kept, first.
    assert after["key_points"][0].startswith("The accounting equation")


def test_nothing_else_in_the_lesson_changes(tmp_path):
    path = _lesson(str(tmp_path))
    before = _read(path)

    script.add_rules(str(tmp_path), commit=True)
    after = _read(path)

    before.pop("key_points")
    after_rest = {k: v for k, v in after.items() if k != "key_points"}
    assert after_rest == before


def test_a_second_run_changes_nothing(tmp_path):
    path = _lesson(str(tmp_path))
    script.add_rules(str(tmp_path), commit=True)
    once = _read(path)

    report = script.add_rules(str(tmp_path), commit=True)

    assert report.files_changed == 0
    assert _read(path) == once


def test_other_units_are_untouched(tmp_path):
    other = _lesson(str(tmp_path), unit="G11-BUS-001")
    before = _read(other)

    script.add_rules(str(tmp_path), commit=True)

    assert _read(other) == before


def test_a_lesson_without_key_points_gets_them(tmp_path):
    path = _lesson(str(tmp_path))
    body = _read(path)
    del body["key_points"]
    with open(path, "w") as f:
        json.dump(body, f)

    script.add_rules(str(tmp_path), commit=True)

    assert len(_read(path)["key_points"]) == 3


def test_running_the_script_by_path_with_no_root(tmp_path):
    """The demo runs `python /app/scripts/<this>.py` with no --root, so the
    default root comes from `config.settings`. Run that way, sys.path[0] is
    scripts/, not backend/, and the import raised ModuleNotFoundError — which is
    how the first demo run died while every test here passed (they all pass
    --root and never import config). This runs it the same way the demo does."""
    _lesson(str(tmp_path))
    env = {**os.environ, "CONTENT_STORE_PATH": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, os.path.join(_SCRIPTS, "add_accounting_golden_rules.py")],
        capture_output=True,
        text=True,
        env=env,
        cwd="/",
    )

    assert proc.returncode == 0, proc.stderr
    assert "DRY-RUN" in proc.stdout
    assert "to change: 1" in proc.stdout


def test_main_reports_and_exits_zero(tmp_path):
    _lesson(str(tmp_path))
    assert script.main(["--root", str(tmp_path)]) == 0
