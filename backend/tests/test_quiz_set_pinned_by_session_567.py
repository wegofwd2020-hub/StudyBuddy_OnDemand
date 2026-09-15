"""
tests/test_quiz_set_pinned_by_session_567.py

The quiz set a student SEES must be the set they are GRADED against (#567).

Reported by Venki 2026-08-10:

    "If you don't answer any questions and leave it for a few mins, it
     automatically takes and shows Set 2... once I start taking the quiz after
     answering 1 or 2 questions, if I don't carry out any activities it takes to
     the next set."

`GET /content/{unit_id}/quiz` mutated state as a side effect of a read:
`get_next_quiz_set()` advanced the per-unit rotation pointer on EVERY call. The
web client inherits a 60s staleTime and React Query's `refetchOnWindowFocus`, so
idling and returning refetched the quiz and rotated it.

Grading was already pinned per session (`quizset:{session_id}`, pitfall #35) —
but that pins GRADING, not DISPLAY. `question_id` is `q1...qN` in every set with
different answers, so nothing errors: the student is silently marked against
questions they were never shown.

Decision taken 2026-08-24, option A: **the session chooses the set.**
`POST /progress/session` rotates once per attempt and pins; `GET .../quiz` serves
what the session pinned rather than advancing anything. That makes the invariant
structural — "the set you see is the set you are graded on" no longer depends on
nobody calling a GET twice.

Two properties that must survive the change, both tested below:
  - a SECOND attempt still rotates to a different set (the reason rotation exists)
  - reusing an unanswered session (#627) must NOT re-rotate: one rotation per
    attempt, not one per page load
"""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt as _jwt

from tests.helpers.lesson_gate import satisfy_lesson_gate
from tests.helpers.token_factory import make_student_token

_UNIT = "G8-MATH-001"
_CURRICULUM = "default-2026-g8"
_JWT_SECRET = "test-secret-do-not-use-in-production-aaaa"


def _token_and_id(seed: str) -> tuple[str, str]:
    token = make_student_token(student_id=seed)
    payload = _jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    return token, payload["student_id"]


async def _insert_student(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Quiz Set Student', $3, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|qs-{student_id.replace('-', '')}",
        f"qs-{student_id.replace('-', '')[-8:]}@test.example.com",
    )
    # A quiz requires the lesson first (2026-09-01). These suites are about
    # quiz mechanics, and their subject is a student who reached the quiz
    # legitimately — so seed the view rather than exempt the test.
    await satisfy_lesson_gate(client, student_id, _UNIT, _CURRICULUM)


async def _start(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT, "curriculum_id": _CURRICULUM},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _end(client: AsyncClient, token: str, session_id: str) -> None:
    r = await client.post(
        f"/api/v1/progress/session/{session_id}/end",
        json={"score": 0, "total_questions": 8},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text


# Reuse the shared fixture rather than hand-rolling one: a bespoke dict drifts
# from QuizResponse and fails validation instead of testing what it meant to.
from tests.test_content import SAMPLE_QUIZ as _SAMPLE_QUIZ  # noqa: E402


@contextlib.contextmanager
def _quiz_content_available(served: list[int]):
    """Serve quiz content so the endpoint returns 200 instead of 404.

    Without this the assertions below only run `if status == 200` and pass
    vacuously in an environment with no content on disk — which would prove
    nothing about the set actually served. `served` records every set number the
    store was asked for.
    """

    async def _fake_file(curriculum_id, unit_id, filename, redis, storage):
        for n in (1, 2, 3):
            if f"quiz_set_{n}_" in filename:
                served.append(n)
                return {**_SAMPLE_QUIZ, "set_number": n}
        raise FileNotFoundError(filename)

    with (
        patch(
            "src.content.router.resolve_curriculum_id",
            new_callable=AsyncMock,
            return_value=_CURRICULUM,
        ),
        patch(
            "src.content.service.resolve_content_curriculum",
            new_callable=AsyncMock,
            side_effect=lambda _u, _c, _s, _p, _v="G8-MATH": (_c, _v),
        ),
        patch(
            "src.content.router.check_content_published",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "src.content.router.check_content_block",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch("src.content.router.get_content_file", side_effect=_fake_file),
    ):
        yield


async def _pinned_set(client: AsyncClient, session_id: str) -> int | None:
    """Read the set recorded on the session row."""
    pool = client._transport.app.state.pool
    return await pool.fetchval(
        "SELECT quiz_set FROM progress_sessions WHERE session_id = $1",
        uuid.UUID(session_id),
    )


# ── The session chooses the set ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_starting_a_session_pins_a_quiz_set(client, db_conn):
    """The set is decided when the attempt starts, not when content is served."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000001")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start(client, token)

    assert session.get("quiz_set") in (1, 2, 3), session
    assert await _pinned_set(client, session["session_id"]) == session["quiz_set"]


@pytest.mark.asyncio
async def test_reopening_the_page_does_not_rotate_the_set(client, db_conn):
    """Venki's case: idle, come back, and the questions change.

    #627 made a page reload reuse the unanswered session; this asserts the reuse
    keeps the SAME set. One rotation per attempt, not one per page load.
    """
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000002")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _start(client, token)
        for _ in range(4):
            again = await _start(client, token)
            assert again["session_id"] == first["session_id"]
            assert again["quiz_set"] == first["quiz_set"], (
                "a page reload rotated the quiz set"
            )


@pytest.mark.asyncio
async def test_a_second_attempt_still_rotates(client, db_conn):
    """Rotation exists for a reason — a retry must not repeat the same questions."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000003")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _start(client, token)
        await _end(client, token, first["session_id"])
        second = await _start(client, token)

    assert second["session_id"] != first["session_id"]
    assert second["quiz_set"] != first["quiz_set"], (
        "the second attempt served the same set as the first"
    )


@pytest.mark.asyncio
async def test_rotation_cycles_through_all_three_sets(client, db_conn):
    """Three attempts should see three different sets, then wrap."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000004")
    await _insert_student(client, student_id)

    seen = []
    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        for _ in range(3):
            s = await _start(client, token)
            seen.append(s["quiz_set"])
            await _end(client, token, s["session_id"])

    assert sorted(seen) == [1, 2, 3], seen


# ── The quiz endpoint serves the pinned set ───────────────────────────────────


@pytest.mark.asyncio
async def test_the_quiz_endpoint_serves_the_sessions_set(client, db_conn):
    """The whole point: display follows the session, not a rotation pointer."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000005")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start(client, token)

    served: list[int] = []
    with _quiz_content_available(served):
        r = await client.get(
            f"/api/v1/content/{_UNIT}/quiz?session_id={session['session_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    assert r.json()["set_number"] == session["quiz_set"], r.json()
    assert served == [session["quiz_set"]], served


@pytest.mark.asyncio
async def test_repeated_quiz_fetches_do_not_rotate(client, db_conn):
    """A refetch — window focus, remount, retry — must be idempotent."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000006")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start(client, token)

    url = f"/api/v1/content/{_UNIT}/quiz?session_id={session['session_id']}"
    headers = {"Authorization": f"Bearer {token}"}
    served: list[int] = []
    sets = []
    with _quiz_content_available(served):
        for _ in range(4):
            r = await client.get(url, headers=headers)
            assert r.status_code == 200, r.text
            sets.append(r.json()["set_number"])

    assert len(set(sets)) == 1, f"the served set changed across refetches: {sets}"
    assert sets[0] == session["quiz_set"]
    # Four fetches, one set — the old behaviour served 1, 2, 3, 1 here.
    assert served == [session["quiz_set"]] * 4, served

    # And the session's pin is untouched by serving.
    assert await _pinned_set(client, session["session_id"]) == session["quiz_set"]


@pytest.mark.asyncio
async def test_another_students_session_is_refused(client, db_conn):
    """A session id is not a capability — it must belong to the caller."""
    token_a, student_a = _token_and_id("f5670000-0000-0000-0000-000000000007")
    token_b, student_b = _token_and_id("f5670000-0000-0000-0000-000000000008")
    await _insert_student(client, student_a)
    await _insert_student(client, student_b)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session_a = await _start(client, token_a)

    r = await client.get(
        f"/api/v1/content/{_UNIT}/quiz?session_id={session_a['session_id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code in (403, 404), r.text


# ── Refreshing mid-attempt must RESUME, not restart ───────────────────────────


@pytest.mark.asyncio
async def test_refreshing_after_answering_resumes_the_same_attempt(client, db_conn):
    """Venki's 26 Aug report — the case #633 did NOT fix.

    #633 pinned the set per session, and #627 reused a session only when it had
    NO answers. Together that meant: answer one question, refresh, and because
    the session now has an answer it is not reused — a NEW session is created
    and the rotation advances. His own data, four sessions on G5-TECH-002 in
    eight minutes:

        13:39:08  set 1  1 answer
        13:46:28  set 2  1 answer   <- refresh
        13:46:52  set 3  1 answer   <- refresh
        13:47:47  set 1  0 answers  <- refresh

    A refresh is not a new attempt. Resuming an answered session is safe: the
    Redis tally is keyed by question_id so re-answering overwrites rather than
    double-counts, and end_session falls back to the persisted answers when the
    tally has expired.
    """
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000009")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _start(client, token)
        # The worker writes the answer row; simulate it having landed.
        pool = client._transport.app.state.pool
        await pool.execute(
            """
            INSERT INTO progress_answers
                (session_id, question_id, student_answer, correct_answer, correct, ms_taken)
            VALUES ($1, 'q1', 0, 0, TRUE, 100)
            """,
            uuid.UUID(first["session_id"]),
        )

        # The refresh.
        resumed = await _start(client, token)

    assert resumed["session_id"] == first["session_id"], (
        "a refresh mid-attempt started a new session instead of resuming"
    )
    assert resumed["quiz_set"] == first["quiz_set"], (
        "the quiz set changed on refresh — the student is shown questions they "
        "are not being graded against"
    )


@pytest.mark.asyncio
async def test_repeated_refreshes_do_not_walk_the_rotation(client, db_conn):
    """His sequence exactly: three refreshes must not cycle 1 -> 2 -> 3."""
    token, student_id = _token_and_id("f5670000-0000-0000-0000-000000000010")
    await _insert_student(client, student_id)

    pool = client._transport.app.state.pool
    sets = []
    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        session = await _start(client, token)
        sets.append(session["quiz_set"])
        for i in range(3):
            await pool.execute(
                """
                INSERT INTO progress_answers
                    (session_id, question_id, student_answer, correct_answer, correct, ms_taken)
                VALUES ($1, $2, 0, 0, TRUE, 100)
                """,
                uuid.UUID(session["session_id"]),
                f"q{i + 1}",
            )
            session = await _start(client, token)
            sets.append(session["quiz_set"])

    assert len(set(sets)) == 1, f"the rotation walked across refreshes: {sets}"
