"""
tests/test_quiz_option_balance_779.py

`balance_options` puts the correct answer at a uniform position (#779).

Across 6,960 demo questions the correct option sat at A 31.2% / B 45.5% /
C 21.6% / D 1.7%: always picking B scored ~45%. Grading is positional, so the fix
reorders the stored options and moves `correct_option` with the correct option.
"""

from __future__ import annotations

import copy
import os
import sys
from collections import Counter

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.quiz_options import balance_options  # noqa: E402


def _question(i: int, texts=("Right", "Wrong 1", "Wrong 2", "Wrong 3"), correct="A") -> dict:
    return {
        "question_id": f"q{i}",
        "question_text": f"Synthetic question number {i}?",
        "question_type": "multiple_choice",
        "options": [
            {"option_id": label, "text": t} for label, t in zip("ABCD", texts, strict=True)
        ],
        "correct_option": correct,
        "explanation": "Because.",
        "difficulty": "easy",
    }


def _quiz(questions: list[dict]) -> dict:
    return {"unit_id": "U-1", "language": "en", "set_number": 1, "questions": questions}


def _correct_text(q: dict) -> str:
    return next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option"])


def test_the_correct_text_is_preserved():
    quiz = _quiz([_question(i) for i in range(50)])
    out = balance_options(quiz, unit_id="U-1", lang="en")
    for before, after in zip(quiz["questions"], out["questions"], strict=True):
        assert _correct_text(after) == _correct_text(before)


def test_the_option_texts_are_preserved_and_relabelled_a_to_d():
    out = balance_options(_quiz([_question(1)]), unit_id="U-1", lang="en")
    q = out["questions"][0]
    assert sorted(o["text"] for o in q["options"]) == ["Right", "Wrong 1", "Wrong 2", "Wrong 3"]
    assert [o["option_id"] for o in q["options"]] == ["A", "B", "C", "D"]


def test_positions_become_uniform():
    """The reported skew, in its worst form: correct is ALWAYS A going in."""
    quiz = _quiz([_question(i) for i in range(2000)])
    out = balance_options(quiz, unit_id="U-1", lang="en")
    share = Counter(q["correct_option"] for q in out["questions"])
    for letter in "ABCD":
        assert 0.22 <= share[letter] / 2000 <= 0.28, share


def test_it_is_deterministic():
    quiz = _quiz([_question(i) for i in range(20)])
    assert balance_options(quiz, unit_id="U-1", lang="en") == balance_options(
        quiz, unit_id="U-1", lang="en"
    )


def test_it_is_idempotent():
    """Re-running the migration or re-publishing must not keep reshuffling."""
    once = balance_options(_quiz([_question(i) for i in range(50)]), unit_id="U-1", lang="en")
    assert balance_options(once, unit_id="U-1", lang="en") == once


def test_the_incoming_order_does_not_matter():
    """Same question, options arriving in a different order -> same result."""
    a = _question(7, texts=("Right", "Wrong 1", "Wrong 2", "Wrong 3"), correct="A")
    b = _question(7, texts=("Wrong 3", "Wrong 1", "Right", "Wrong 2"), correct="C")
    out_a = balance_options(_quiz([a]), unit_id="U-1", lang="en")["questions"][0]
    out_b = balance_options(_quiz([b]), unit_id="U-1", lang="en")["questions"][0]
    assert out_a["options"] == out_b["options"]
    assert out_a["correct_option"] == out_b["correct_option"]


def test_duplicate_text_options_stay_idempotent_and_correct():
    """#754 content: the correct answer appears twice. Grading accepts either copy,
    but the letter must not flip between runs."""
    q = _question(3, texts=("USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"), correct="B")
    once = balance_options(_quiz([q]), unit_id="U-1", lang="en")
    twice = balance_options(once, unit_id="U-1", lang="en")
    assert twice == once
    assert _correct_text(once["questions"][0]) == "USD 35,000"


def test_an_unresolvable_correct_option_is_left_alone():
    """A content defect the grader logs and skips. Reordering it would hide it."""
    q = _question(1, correct="Z")
    out = balance_options(_quiz([q]), unit_id="U-1", lang="en")
    assert out["questions"][0] == q


def test_the_input_is_not_mutated():
    quiz = _quiz([_question(i) for i in range(5)])
    snapshot = copy.deepcopy(quiz)
    balance_options(quiz, unit_id="U-1", lang="en")
    assert quiz == snapshot


def test_other_fields_are_untouched():
    quiz = _quiz([_question(1)])
    quiz["generated_at"] = "2026-09-16T00:00:00Z"
    out = balance_options(quiz, unit_id="U-1", lang="en")
    assert out["generated_at"] == quiz["generated_at"]
    for key in ("question_id", "question_text", "explanation", "difficulty"):
        assert out["questions"][0][key] == quiz["questions"][0][key]


def test_whitespace_variant_wrong_options_stay_idempotent():
    """M-1 (final review): two WRONG options with equal normalised text but
    different raw text (a double space) used to tie-break on option_id, which
    is position-derived after relabelling — a second run could reorder them
    (~50% observed). The tie-break must be the option's own content instead."""
    questions = [
        _question(
            i,
            texts=("USD 30,000", "USD  30,000", "USD 40,000", "Correct answer"),
            correct="D",
        )
        for i in range(200)
    ]
    quiz = _quiz(questions)
    once = balance_options(quiz, unit_id="U-1", lang="en")
    twice = balance_options(once, unit_id="U-1", lang="en")
    assert twice == once
