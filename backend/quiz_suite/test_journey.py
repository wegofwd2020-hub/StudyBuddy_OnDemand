"""
The path a student actually walks. This is the tier that would have failed on
#524: the session's curriculum_id must be the RESOLVED one, or grading 404s.
"""

from __future__ import annotations

import pytest

from quiz_suite import constants as C

pytestmark = pytest.mark.quiz_live


async def start_session(api, headers, unit_id=C.UNIT_QUIZ, body=None):
    r = await api.post("/progress/session", json=body or {"unit_id": unit_id}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def serve_quiz(api, headers, unit_id=C.UNIT_QUIZ) -> dict:
    r = await api.get(f"/content/{unit_id}/quiz", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def answer_all(api, headers, session_id, key_for_set) -> list[dict]:
    """Answer q1..q3 correctly per the fixture key. Returns the server verdicts."""
    verdicts = []
    for qid, correct_index in key_for_set.items():
        r = await api.post(
            f"/progress/session/{session_id}/answer",
            json={"question_id": qid, "student_answer": correct_index, "ms_taken": 10},
            headers=headers,
        )
        assert r.status_code == 200, f"{qid}: {r.status_code} {r.text}"
        verdicts.append(r.json())
    return verdicts


@pytest.mark.asyncio
async def test_session_uses_the_resolved_curriculum_not_the_body(api, auth_a):
    """#524: a lying body must not decide what grading looks up."""
    session = await start_session(api, auth_a, body={"unit_id": C.UNIT_QUIZ, "curriculum_id": "default"})
    assert session["curriculum_id"] == C.CURRICULUM_ID


@pytest.mark.asyncio
async def test_session_without_curriculum_id_resolves(api, auth_a):
    session = await start_session(api, auth_a)
    assert session["curriculum_id"] == C.CURRICULUM_ID


@pytest.mark.asyncio
async def test_unaffiliated_student_falls_back_to_default_package(api, auth_b):
    """Student B has no school. Asserts the id string, not that content exists."""
    session = await start_session(api, auth_b)
    assert session["curriculum_id"] == f"default-{C.YEAR}-g{C.GRADE}"


@pytest.mark.asyncio
async def test_full_run_scores_what_the_student_earned(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    verdicts = await answer_all(api, auth_a, session["session_id"], key)
    assert all(v["correct"] for v in verdicts), verdicts

    r = await api.post(f"/progress/session/{session['session_id']}/end", json={}, headers=auth_a)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["score"] == len(key)
    assert result["total_questions"] == len(key)
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_session_is_attributed_to_a_real_subject_and_grade(api, auth_a, fixture_data):
    """
    #524's silent second-order damage: create_session stored grade=0 and
    subject="unknown" when it looked the unit up under the wrong
    curriculum_id. No error, no 404 — analytics simply attributed the quiz
    to nothing.

    Only `grade` can actually go red here for a #524-style regression.
    `subject` cannot: GET /progress/student never surfaces the raw stored
    column. get_raw_history() (backend/src/progress/service.py:354-431)
    resolves every row's subject through display_subject() fed by
    resolve_subject_labels() (backend/src/core/subjects.py:70-102, 105-123)
    before returning it — and that resolver's query filters by unit_id ALONE
    (subjects.py:97, `WHERE cu.unit_id = ANY($1::text[])`), with no
    curriculum_id in the join condition. This is deliberate — the #462 fix
    for "Subject shows 'Unknown' everywhere". The fixture's QS-TEST-001
    exists exactly once in curriculum_units, so its label ("Science")
    resolves regardless of which curriculum_id the session was created
    under; even a session persisted with subject="unknown" reports "Science"
    through this endpoint. `grade` has no such override (service.py:403 is a
    direct passthrough of the stored column), so it is the one that
    genuinely detects the regression.
    """
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)
    await answer_all(api, auth_a, session["session_id"], key)
    await api.post(f"/progress/session/{session['session_id']}/end", json={}, headers=auth_a)

    r = await api.get("/progress/student", headers=auth_a)
    assert r.status_code == 200, r.text
    rows = [s for s in r.json()["sessions"] if s["unit_id"] == C.UNIT_QUIZ]
    assert rows, "the completed session is missing from history"
    # `grade` is the load-bearing assertion for #524 detection (see
    # docstring). `subject` cannot fail here — display_subject()/
    # resolve_subject_labels() mask the stored value by resolving from
    # unit_id alone (#462 fix, subjects.py:97) — kept for documentation
    # value only.
    assert rows[0].get("subject") not in (None, "", "unknown")
    assert rows[0].get("grade") not in (None, 0)


@pytest.mark.asyncio
async def test_second_attempt_rotates_the_set_and_grades_against_it(api, auth_a, fixture_data):
    first = await serve_quiz(api, auth_a)
    second = await serve_quiz(api, auth_a)
    assert first["set_number"] != second["set_number"], "rotation did not advance"

    session = await start_session(api, auth_a)
    key = fixture_data["answer_key"][str(second["set_number"])]
    verdicts = await answer_all(api, auth_a, session["session_id"], key)
    assert all(v["correct"] for v in verdicts), "graded against the wrong set"
