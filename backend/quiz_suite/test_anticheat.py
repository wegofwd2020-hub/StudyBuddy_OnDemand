"""
The guarantees #506 introduced, asserted against the running app.

The existing backend tests assert these against a stubbed answer key, which is
how #524 slipped through — the stub is the thing that hides the bug.
"""

from __future__ import annotations

import pytest

from quiz_suite import constants as C
from quiz_suite.test_journey import serve_quiz, start_session

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_served_quiz_leaks_no_answer_key(api, auth_a):
    """
    Asserted on the RAW body, not the parsed model. Testing the model tests the
    serializer; testing the body tests the wire.
    """
    r = await api.get(f"/content/{C.UNIT_QUIZ}/quiz", headers=auth_a)
    assert r.status_code == 200
    raw = r.text
    for forbidden in ("correct_option", "correct_index", "correct_answer"):
        assert forbidden not in raw, f"{forbidden} leaked in the served quiz"


@pytest.mark.asyncio
async def test_client_claiming_correctness_is_ignored(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    wrong_index = (key["q1"] + 1) % 3
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={
            "question_id": "q1",
            "student_answer": wrong_index,
            "correct": True,  # ignored
            "correct_answer": wrong_index,  # ignored
            "ms_taken": 10,
        },
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is False, "the server took the client's word for it"


@pytest.mark.asyncio
async def test_client_cannot_post_its_own_score(api, auth_a, fixture_data):
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)

    for qid, correct_index in key.items():
        await api.post(
            f"/progress/session/{session['session_id']}/answer",
            json={"question_id": qid, "student_answer": (correct_index + 1) % 3, "ms_taken": 10},
            headers=auth_a,
        )
    r = await api.post(
        f"/progress/session/{session['session_id']}/end",
        json={"score": 99, "total_questions": 99},
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 0


@pytest.mark.asyncio
async def test_revisiting_a_question_does_not_inflate_the_score(api, auth_a, fixture_data):
    """
    #532: the skip-and-return UI lets a student re-answer a question, so the
    server tally must be idempotent per question. Answer two of three correctly,
    then re-submit a correct answer a second time — the score must stay at 2, not
    climb to 3. Before the per-question hash (the old blind INCR tally) this
    re-submit double-counted, and end_session's clamp only capped it at the total,
    so a 2/3 run could present as 3/3.
    """
    quiz = await serve_quiz(api, auth_a)
    key = fixture_data["answer_key"][str(quiz["set_number"])]
    session = await start_session(api, auth_a)
    sid = session["session_id"]

    async def answer(qid: str, index: int) -> None:
        r = await api.post(
            f"/progress/session/{sid}/answer",
            json={"question_id": qid, "student_answer": index, "ms_taken": 10},
            headers=auth_a,
        )
        assert r.status_code == 200, r.text

    await answer("q1", key["q1"])  # correct
    await answer("q2", key["q2"])  # correct
    await answer("q3", (key["q3"] + 1) % 3)  # wrong
    await answer("q1", key["q1"])  # revisit q1, still correct — must not count twice

    r = await api.post(f"/progress/session/{sid}/end", json={}, headers=auth_a)
    assert r.status_code == 200, r.text
    assert r.json()["score"] == 2, "revisiting a correct answer inflated the score"


@pytest.mark.asyncio
async def test_graded_set_is_pinned_for_the_session(api, auth_a, fixture_data):
    """
    Answer q1, force the rotation pointer forward by re-fetching the quiz, then
    answer q2. Both must be graded against the set pinned at session start —
    the sets have different answers, so a re-read pointer fails here.

    Discriminating power: resolve_session_quiz_set (backend/src/progress/service.py)
    pins the rotation pointer into `quiz_session_set_key(session_id)` on the FIRST
    answer of a session and reuses that pinned value for every later answer in the
    same session, ignoring where the per-unit rotation pointer
    (`quiz_set_key(student_id, unit_id)`) has moved to since. A naive
    implementation that re-reads the per-unit rotation pointer on every answer
    instead of pinning it per-session would grade the q1 answer correctly (the
    pointer hasn't moved yet), then — after the `serve_quiz` call below advances
    the per-unit pointer to a different set — grade q2 against that NEW set's
    key. Because the fixture is built so q2's correct index differs between sets
    (same question_id, different answer per set), submitting the ORIGINALLY
    pinned set's correct index for q2 would be marked wrong under a re-read
    implementation, failing this test's final assertion. Under real per-session
    pinning it stays correct.
    """
    quiz = await serve_quiz(api, auth_a)
    pinned = str(quiz["set_number"])
    key = fixture_data["answer_key"][pinned]
    session = await start_session(api, auth_a)

    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": key["q1"], "ms_taken": 10},
        headers=auth_a,
    )
    assert r.json()["correct"] is True

    await serve_quiz(api, auth_a)  # advances the per-unit rotation pointer

    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q2", "student_answer": key["q2"], "ms_taken": 10},
        headers=auth_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True, "later answer was graded against a different set"


@pytest.mark.asyncio
async def test_another_students_session_is_forbidden(api, auth_a, auth_b):
    session = await start_session(api, auth_a)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "q1", "student_answer": 0, "ms_taken": 10},
        headers=auth_b,
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_unknown_question_is_a_400_not_a_500(api, auth_a):
    session = await start_session(api, auth_a)
    r = await api.post(
        f"/progress/session/{session['session_id']}/answer",
        json={"question_id": "does-not-exist", "student_answer": 0, "ms_taken": 10},
        headers=auth_a,
    )
    assert r.status_code == 400, r.text
