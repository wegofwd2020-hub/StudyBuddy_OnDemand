"""
Sweep REAL on-disk content — not the fixture — for quiz data that would grade
students incorrectly.

The sharp checks mirror get_quiz_answer_key's own silent-skip branches
(backend/src/content/service.py): it SKIPS any question with a missing
question_id, and SKIPS any question whose correct_option names an option that
doesn't exist. Either produces a question that silently grades every student
wrong, and nothing else in the codebase notices.
"""

from __future__ import annotations

import glob
import json
import os

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


def _real_quiz_files() -> list[str]:
    """Every quiz set on disk except the suite's own fixture."""
    pattern = os.path.join(C.CONTENT_ROOT, "*", "*", "quiz_set_*.json")
    return [p for p in glob.glob(pattern) if f"/{C.CURRICULUM_ID}/" not in p]


def test_real_content_is_present_or_loudly_skipped():
    files = _real_quiz_files()
    if not files:
        pytest.skip(
            "NO REAL QUIZ CONTENT ON THIS BOX (0 quiz_set_*.json outside the fixture) — "
            "the integrity sweep checked nothing. This is a skip, not a pass."
        )
    assert files


def test_every_quiz_set_parses_and_grades():
    files = _real_quiz_files()
    if not files:
        pytest.skip("no real quiz content on this box")

    broken: list[str] = []
    for path in files:
        rel = os.path.relpath(path, C.CONTENT_ROOT)
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            broken.append(f"{rel}: unreadable ({exc})")
            continue

        questions = data.get("questions")
        if not questions:
            broken.append(f"{rel}: no questions")
            continue

        for question in questions:
            if not question.get("question_id"):
                broken.append(f"{rel}: question missing question_id")
                continue
            qid = question["question_id"]
            options = question.get("options") or []
            correct = question.get("correct_option")
            if not options:
                broken.append(f"{rel} {qid}: no options")
                continue
            if correct is None:
                broken.append(f"{rel} {qid}: no correct_option")
                continue
            if not any(o.get("option_id") == correct for o in options):
                broken.append(
                    f"{rel} {qid}: correct_option {correct!r} is not among "
                    f"{[o.get('option_id') for o in options]} — every student is graded wrong here"
                )

    assert not broken, "content that would misgrade students:\n" + "\n".join(broken)
