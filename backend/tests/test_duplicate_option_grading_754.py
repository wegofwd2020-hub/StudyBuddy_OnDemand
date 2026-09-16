"""
tests/test_duplicate_option_grading_754.py

Quiz options that render identically (#754).

Venki, 2026-09-14:

    "Student selected USD 35,000 which was marked wrong but the correct answer
     shown was also USD 35,000."

The grader was not wrong. `G11-ACC-001/quiz_set_2_en.json` q7 ships:

    [0] A: 'USD 35,000'   <- correct_option
    [1] B: 'USD 35,000'
    [2] C: 'USD 30,000'
    [3] D: 'USD 36,500'

A student who reads the paper and picks "USD 35,000" has a one-in-two chance of
clicking index 1, which is graded against index 0 and marked wrong. The reveal
then highlights index 0 — the same words they chose. That is the whole report:
not a grading bug, a question with two correct answers and no way to pick the
one that counts.

A sweep of the demo store found 9 such questions in 6,960, ALL of them with the
correct option at index 0 and a copy of it later in the list. The generator emits
the answer, then repeats it as a distractor — so this recurs until generation
stops it.

Two defects, fixed at two layers:

  1. The pipeline must never WRITE a question whose options are not distinguish-
     able (`validate_quiz`). That is the root cause and the only fix that stops
     new ones appearing.
  2. Grading must honour what the student could actually see. Options are chosen
     by POSITION, but what the student picked is the TEXT; when two positions
     carry the same text they are the same answer, and both must grade correct.
     This is what repairs the 9 questions already live, without a regen.

Case is NOT normalised away, and that restriction is load-bearing — the same
sweep found 4 questions whose options differ only in case and are perfectly
answerable: 'Bb — heterozygous' vs 'bB — heterozygous' (genotype notation),
"['Running', ...]" vs "['running', ...]" (Python case-sensitivity), and
'$\\sqrt{2gH}$' vs '$\\sqrt{2gh}$' (H and h are different quantities). Folding
case would condemn all four as defects and, worse, would grade a wrong answer
correct.
"""

from __future__ import annotations

import os
import sys
import uuid
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest
from httpx import AsyncClient
from jose import jwt as _jwt

from src.content.service import _parse_quiz_answer_key
from tests.helpers.lesson_gate import satisfy_lesson_gate
from tests.helpers.token_factory import make_student_token


def _validate_quiz(data: dict) -> None:
    """`pipeline/` is a sibling of `backend/` and is not on the api container's
    path. Imported lazily, inside a function, for the same reason
    tests/test_prompt_json_escapes.py does it: isort hoists a module-level
    import above the sys.path line that makes it work.
    """
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from pipeline.schemas import validate_quiz

    validate_quiz(data)


_UNIT = "G8-MATH-001"
_CURRICULUM = "default-2026-g8"
_JWT_SECRET = "test-secret-do-not-use-in-production-aaaa"


def _question(qid: str, texts: list[str], correct: str = "A") -> dict:
    """One question whose option TEXTS are given positionally, ids always A..D."""
    return {
        "question_id": qid,
        "question_text": f"Question {qid} with enough text to satisfy the schema?",
        "question_type": "multiple_choice",
        "options": [
            {"option_id": oid, "text": text}
            for oid, text in zip("ABCD", texts)
        ],
        "correct_option": correct,
        "explanation": "Because that is the answer.",
        "difficulty": "medium",
    }


def _body(*questions: dict) -> dict:
    return {"questions": list(questions)}


# ── Layer 2: grading honours the text the student saw ─────────────────────────


def test_a_duplicate_of_the_correct_option_also_grades_correct():
    """Venki's exact question. Index 1 reads 'USD 35,000' and so does index 0."""
    key = _parse_quiz_answer_key(
        _body(_question("q7", ["USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"])),
        _CURRICULUM,
        "G11-ACC-001",
        2,
    )

    assert key["q7"]["index"] == 0, "the canonical index is unchanged"
    assert set(key["q7"]["accepted"]) == {0, 1}


def test_a_genuinely_wrong_option_is_still_wrong():
    """The narrowing that matters: only text-IDENTICAL options are accepted."""
    key = _parse_quiz_answer_key(
        _body(_question("q7", ["USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"])),
        _CURRICULUM,
        "G11-ACC-001",
        2,
    )

    assert 2 not in key["q7"]["accepted"], "'USD 30,000' is a different answer"
    assert 3 not in key["q7"]["accepted"]


def test_options_differing_only_in_case_are_NOT_merged():
    """'Bb' and 'bB' are different genotypes; 'H' and 'h' different quantities.

    Folding case here would mark a wrong answer correct — strictly worse than
    the bug being fixed.
    """
    key = _parse_quiz_answer_key(
        _body(
            _question(
                "q6",
                [
                    "BB — homozygous dominant",
                    "Bb — heterozygous",
                    "bb — homozygous recessive",
                    "bB — heterozygous",
                ],
                correct="B",
            )
        ),
        _CURRICULUM,
        "G7-SCI-004",
        3,
    )

    assert key["q6"]["index"] == 1
    assert set(key["q6"]["accepted"]) == {1}, "'bB' is not 'Bb'"


def test_surrounding_whitespace_does_not_create_a_second_answer():
    """' USD 35,000 ' and 'USD 35,000' are the same words on screen; HTML
    collapses the difference, so grading must too."""
    key = _parse_quiz_answer_key(
        _body(_question("q1", ["USD 35,000", "  USD 35,000  ", "USD 30,000", "USD 1"])),
        _CURRICULUM,
        _UNIT,
        1,
    )

    assert set(key["q1"]["accepted"]) == {0, 1}


def test_an_ordinary_question_accepts_exactly_one_index():
    """The overwhelmingly common case must be untouched."""
    key = _parse_quiz_answer_key(
        _body(_question("q2", ["4", "5", "6", "7"], correct="C")),
        _CURRICULUM,
        _UNIT,
        1,
    )

    assert key["q2"]["index"] == 2
    assert set(key["q2"]["accepted"]) == {2}


def test_blank_option_texts_do_not_collapse_into_each_other():
    """Two empty strings are equal, but an empty option is a content defect, not
    evidence that the student chose right. Accepting them would hand a free mark
    to whoever clicks a blank."""
    key = _parse_quiz_answer_key(
        _body(_question("q3", ["", "", "42", "7"], correct="C")),
        _CURRICULUM,
        _UNIT,
        1,
    )

    assert set(key["q3"]["accepted"]) == {2}


# ── Layer 1: the pipeline must not write such a question at all ───────────────


def _quiz_set(*questions: dict) -> dict:
    """A full, schema-valid quiz set (8 questions) carrying `questions` first."""
    filler = [
        _question(f"qf{i}", [f"{i}a", f"{i}b", f"{i}c", f"{i}d"])
        for i in range(len(questions) + 1, 9)
    ]
    return {
        "unit_id": _UNIT,
        "set_number": 1,
        "language": "en",
        "questions": [*questions, *filler],
        "total_questions": 8,
        "estimated_duration_minutes": 10,
        "passing_score": 6,
        "generated_at": "2026-09-16T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }


def test_validate_quiz_rejects_indistinguishable_options():
    """The root-cause fix: content like this never reaches the store.

    `build_grade` retries a ValidationError up to 3x then fails the unit, so
    raising here is what turns "student graded wrong" into "unit rebuilt".
    """
    bad = _quiz_set(
        _question("q1", ["USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"])
    )

    with pytest.raises(jsonschema.ValidationError) as exc:
        _validate_quiz(bad)

    assert "q1" in str(exc.value)


def test_validate_quiz_accepts_options_differing_only_in_case():
    """Same narrowing as the grader, enforced at the other end of the pipeline.

    If these two checks disagreed, the pipeline would reject content the grader
    handles correctly — or worse, admit content the grader cannot.
    """
    ok = _quiz_set(
        _question(
            "q1",
            [
                "BB — homozygous dominant",
                "Bb — heterozygous",
                "bb — homozygous recessive",
                "bB — heterozygous",
            ],
            correct="B",
        )
    )

    _validate_quiz(ok)  # must not raise


def test_validate_quiz_still_accepts_an_ordinary_set():
    _validate_quiz(_quiz_set())


# ── End to end: the student's answer, through the real endpoint ───────────────


def _token_and_id(seed: str) -> tuple[str, str]:
    token = make_student_token(student_id=seed)
    payload = _jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    return token, payload["student_id"]


async def _insert_student(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Dup Option Student', $3, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|dup-{student_id.replace('-', '')}",
        f"dup-{student_id.replace('-', '')[-8:]}@test.example.com",
    )
    await satisfy_lesson_gate(client, student_id, _UNIT, _CURRICULUM)


@pytest.mark.asyncio
async def test_the_student_who_picked_the_duplicate_is_marked_correct(client, db_conn):
    """The report, end to end: pick index 1 of two identical options, and the
    summary must say correct."""
    token, student_id = _token_and_id("d7540000-0000-0000-0000-000000000001")
    await _insert_student(client, student_id)

    key = _parse_quiz_answer_key(
        _body(_question("q1", ["USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"])),
        _CURRICULUM,
        _UNIT,
        1,
    )

    with patch(
        "src.progress.router.resolve_quiz_answer_key",
        new_callable=AsyncMock,
        return_value=key,
    ):
        started = await client.post(
            "/api/v1/progress/session",
            json={"unit_id": _UNIT, "curriculum_id": _CURRICULUM},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["session_id"]

        answered = await client.post(
            f"/api/v1/progress/session/{session_id}/answer",
            json={"question_id": "q1", "student_answer": 1, "ms_taken": 4000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert answered.status_code == 200, answered.text

        ended = await client.post(
            f"/api/v1/progress/session/{session_id}/end",
            json={"score": 0, "total_questions": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ended.status_code == 200, ended.text
        body = ended.json()

    assert body["score"] == 1, "the student chose the right words and must be scored for it"

    reveal = {r["question_id"]: r for r in body.get("reveal", [])}
    assert reveal["q1"]["correct"] is True
    assert reveal["q1"]["your_answer"] == 1
    # The highlight must land on what they clicked, not on the other copy of the
    # same words -- that mismatch IS the thing Venki reported seeing.
    assert reveal["q1"]["correct_index"] == 1


@pytest.mark.asyncio
async def test_a_wrong_answer_is_still_wrong_end_to_end(client, db_conn):
    """The negative case. Without this the fix above could mark everything
    correct and every assertion here would still pass."""
    token, student_id = _token_and_id("d7540000-0000-0000-0000-000000000002")
    await _insert_student(client, student_id)

    key = _parse_quiz_answer_key(
        _body(_question("q1", ["USD 35,000", "USD 35,000", "USD 30,000", "USD 36,500"])),
        _CURRICULUM,
        _UNIT,
        1,
    )

    with patch(
        "src.progress.router.resolve_quiz_answer_key",
        new_callable=AsyncMock,
        return_value=key,
    ):
        started = await client.post(
            "/api/v1/progress/session",
            json={"unit_id": _UNIT, "curriculum_id": _CURRICULUM},
            headers={"Authorization": f"Bearer {token}"},
        )
        session_id = started.json()["session_id"]

        await client.post(
            f"/api/v1/progress/session/{session_id}/answer",
            json={"question_id": "q1", "student_answer": 2, "ms_taken": 4000},
            headers={"Authorization": f"Bearer {token}"},
        )
        ended = await client.post(
            f"/api/v1/progress/session/{session_id}/end",
            json={"score": 0, "total_questions": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        body = ended.json()

    assert body["score"] == 0, "'USD 30,000' is not the answer"
    reveal = {r["question_id"]: r for r in body.get("reveal", [])}
    assert reveal["q1"]["correct"] is False
    assert reveal["q1"]["correct_index"] == 0, "wrong answer: reveal the canonical option"
