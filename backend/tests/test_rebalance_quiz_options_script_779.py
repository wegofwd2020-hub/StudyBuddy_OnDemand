"""
tests/test_rebalance_quiz_options_script_779.py

The one-off migration that balances existing quiz content (#779).
Dry-run by default; `--commit` writes only files whose answer key still grades
the same question to the same text.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import rebalance_quiz_options as script  # noqa: E402


def _quiz(unit_id: str, model: str = "claude-sonnet-4-6") -> dict:
    return {
        "unit_id": unit_id,
        "language": "en",
        "set_number": 1,
        "model": model,
        "questions": [
            {
                "question_id": f"q{i}",
                "question_text": f"Rebalance script question {unit_id} {i}?",
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": "A", "text": "Right"},
                    {"option_id": "B", "text": "Wrong 1"},
                    {"option_id": "C", "text": "Wrong 2"},
                    {"option_id": "D", "text": "Wrong 3"},
                ],
                "correct_option": "A",
                "explanation": "Because.",
                "difficulty": "easy",
            }
            for i in range(1, 41)
        ],
    }


def _write(root, cid: str, unit: str, body: dict, name: str = "quiz_set_1_en.json") -> str:
    d = os.path.join(root, "curricula", cid, unit)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w") as f:
        json.dump(body, f)
    return path


def _read(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def test_dry_run_writes_nothing(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    before = _read(path)

    report = script.rebalance(str(tmp_path), commit=False)

    assert _read(path) == before
    assert report.files_seen == 1
    assert report.files_changed == 1
    assert report.before["A"] == 40
    assert report.after["A"] < 40


def test_commit_writes_balanced_files_that_grade_the_same(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))

    report = script.rebalance(str(tmp_path), commit=True)
    after = _read(path)

    assert report.files_changed == 1
    assert {q["correct_option"] for q in after["questions"]} != {"A"}
    for q in after["questions"]:
        assert (
            next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"])
            == "Right"
        )


def test_a_second_run_changes_nothing(tmp_path):
    _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    script.rebalance(str(tmp_path), commit=True)

    report = script.rebalance(str(tmp_path), commit=True)

    assert report.files_changed == 0


def test_placeholder_content_is_skipped(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1", model="dev-placeholder"))
    before = _read(path)

    report = script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before
    assert report.skipped_placeholder == 1


def test_non_quiz_files_are_ignored(tmp_path):
    _write(tmp_path, "c1", "U-1", {"sections": []}, name="lesson_en.json")

    report = script.rebalance(str(tmp_path), commit=True)

    assert report.files_seen == 0


def test_an_invariant_violation_aborts_without_writing(tmp_path):
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    before = _read(path)

    def _corrupt(quiz, *, unit_id, lang):
        broken = json.loads(json.dumps(quiz))
        broken["questions"][0]["options"][0]["text"] = "Something else"
        return broken

    with patch.object(script, "balance_options", _corrupt):
        with pytest.raises(script.RebalanceInvariantError):
            script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before


def test_main_returns_2_on_violation(tmp_path):
    _write(tmp_path, "c1", "U-1", _quiz("U-1"))

    def _corrupt(quiz, *, unit_id, lang):
        broken = json.loads(json.dumps(quiz))
        broken["questions"][0]["correct_option"] = "B"
        return broken

    with patch.object(script, "balance_options", _corrupt):
        assert script.main(["--root", str(tmp_path), "--commit"]) == 2


def test_malformed_json_aborts_cleanly(tmp_path):
    """M-2 (final review): malformed JSON used to escape as a raw
    json.JSONDecodeError traceback; it must abort cleanly instead (exit 2)."""
    d = os.path.join(tmp_path, "curricula", "c1", "U-1")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "quiz_set_1_en.json"), "w") as f:
        f.write("{not json")

    assert script.main(["--root", str(tmp_path), "--commit"]) == 2


def test_a_changed_question_text_aborts_without_writing(tmp_path):
    """M-3 (final review): `_verify` only checked options and correct text, so
    a change to `question_text` (the ADR-008 stable_question_id input) or
    `explanation` would pass silently."""
    path = _write(tmp_path, "c1", "U-1", _quiz("U-1"))
    before = _read(path)

    def _alter_question_text(quiz, *, unit_id, lang):
        result = json.loads(json.dumps(quiz))
        result["questions"][0]["question_text"] = "A completely different question?"
        return result

    with patch.object(script, "balance_options", _alter_question_text):
        with pytest.raises(script.RebalanceInvariantError):
            script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before


def test_a_reordered_unresolvable_question_aborts_without_writing(tmp_path):
    quiz = _quiz("U-1")
    quiz["questions"][0]["correct_option"] = "Z"  # unresolvable
    path = _write(tmp_path, "c1", "U-1", quiz)
    before = _read(path)

    def _reorder_first_question(body, *, unit_id, lang):
        result = json.loads(json.dumps(body))
        result["questions"][0]["options"] = result["questions"][0]["options"][::-1]
        return result

    with patch.object(script, "balance_options", _reorder_first_question):
        with pytest.raises(script.RebalanceInvariantError):
            script.rebalance(str(tmp_path), commit=True)

    assert _read(path) == before
