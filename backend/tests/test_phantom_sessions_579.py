"""
tests/test_phantom_sessions_579.py

Opening a quiz page must not count as taking the quiz (issue #579).

`startNew()` in the quiz page calls `POST /progress/session` on mount, so every
page load wrote a `progress_sessions` row. Open a quiz, wander off, come back:
two rows. Never finish: they persist forever. On the demo database that left
**78 session rows for 7 units, only 16 of them carrying a score** — roughly four
in five rows were page loads nobody ever answered.

Venki reported the same defect three ways without them looking related:
  - "more than 10 records with same data" in Progress History
  - "Recent activity ... looks it is not the case" (same feed)
  - "Quizzes completed shows 4 but I completed 2"
  - "QUIZ ATTEMPTS 85" on the 30-day Overview vs 8 on the 7-day

One rule fixes all of them: **a session with no answers that was never completed
is not an attempt.** It should not be created, shown, or counted.

Both halves are needed and neither is sufficient:
  - reuse only stops NEW rows accumulating; the demo already holds 78
  - filtering only hides them; the rows keep breeding

Deliberately NOT deleting the existing rows: they are student educational
records under FERPA, and a display/count fix is reversible where a DELETE is not.

Guard against over-correcting: a session the student actually answered and then
abandoned is real work and must still appear. #465 (attempt numbers assigned at
completion) must not regress either — that bug produced the duplicate
"Attempt #2" cards this issue's residue sits next to.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

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
        VALUES ($1, $2, 'Phantom Student', $3, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        # The FULL id — these seeds differ only in their last characters, and
        # truncating collided on students_external_auth_id_key.
        f"auth0|ph-{student_id.replace('-', '')}",
        f"ph-{student_id.replace('-', '')[-8:]}@test.example.com",
    )
    # A quiz requires the lesson first (2026-09-01). These suites are about
    # quiz mechanics, and their subject is a student who reached the quiz
    # legitimately — so seed the view rather than exempt the test.
    await satisfy_lesson_gate(client, student_id, _UNIT, _CURRICULUM)


async def _open_quiz_page(client: AsyncClient, token: str) -> dict:
    """Exactly what the quiz page does on mount."""
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT, "curriculum_id": _CURRICULUM},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _finish(client: AsyncClient, token: str, session_id: str, score: int = 8) -> None:
    r = await client.post(
        f"/api/v1/progress/session/{session_id}/end",
        json={"score": score, "total_questions": 8},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text


async def _record_answer_row(client: AsyncClient, session_id: str) -> None:
    """Write a progress_answers row directly.

    The endpoint dispatches this write to Celery (fire-and-forget) and the task
    is mocked out in tests, so the row would never appear. Inserting it directly
    is how a test represents "the worker has written the answer".
    """
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO progress_answers
            (session_id, question_id, student_answer, correct_answer, correct, ms_taken)
        VALUES ($1, 'q1', 0, 0, TRUE, 100)
        """,
        uuid.UUID(session_id),
    )


async def _session_count(client: AsyncClient, student_id: str) -> int:
    pool = client._transport.app.state.pool
    return await pool.fetchval(
        "SELECT COUNT(*) FROM progress_sessions WHERE student_id = $1",
        uuid.UUID(student_id),
    )


async def _history(client: AsyncClient, token: str) -> dict:
    r = await client.get(
        "/api/v1/progress/student", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── Source: stop creating a row per page load ─────────────────────────────────


@pytest.mark.asyncio
async def test_reopening_the_quiz_page_does_not_add_a_session(client, db_conn):
    """Five page loads, no answers, one session row.

    This is Venki's "more than 10 records with same data", at source.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000001")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _open_quiz_page(client, token)
        for _ in range(4):
            again = await _open_quiz_page(client, token)
            assert again["session_id"] == first["session_id"], (
                "a page reload opened a second session"
            )

    assert await _session_count(client, student_id) == 1


@pytest.mark.asyncio
async def test_a_session_the_student_answered_is_resumed_not_restarted(client, db_conn):
    """CORRECTED (#567). This test originally asserted the opposite.

    #579 reused only sessions with NO answers, on the reasoning that an answered
    session is "real work belonging to its own attempt" and merging would land a
    re-answered q1 against the earlier one.

    That was wrong, and Venki found the cost on 26 Aug: answer one question,
    refresh, and because the session now has an answer it was not reused — a new
    session opened and the quiz set rotated. His live data showed sets
    1 -> 2 -> 3 -> 1 across four sessions on one unit in eight minutes, so he was
    shown questions he was not being graded against.

    A refresh is not a new attempt. Resuming is safe: the Redis tally is keyed by
    question_id so re-answering overwrites rather than double-counts, and
    end_session falls back to the persisted answers when the tally has expired.
    "Try Again" still starts fresh, because that session is completed.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000002")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _open_quiz_page(client, token)
        await _record_answer_row(client, first["session_id"])
        second = await _open_quiz_page(client, token)

    assert second["session_id"] == first["session_id"], (
        "a refresh after answering started a new attempt"
    )
    assert await _session_count(client, student_id) == 1


@pytest.mark.asyncio
async def test_try_again_after_finishing_starts_a_fresh_session(client, db_conn):
    """A completed session must never be reused — "Try Again" is a new attempt."""
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000003")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        first = await _open_quiz_page(client, token)
        await _finish(client, token, first["session_id"])
        second = await _open_quiz_page(client, token)

    assert second["session_id"] != first["session_id"]
    assert await _session_count(client, student_id) == 2


@pytest.mark.asyncio
async def test_attempt_numbers_stay_sequential_across_reloads(client, db_conn):
    """Don't regress #465: completed attempts number 1, 2 — reloads don't count.

    Before #465 the eagerly-created sessions all shared an attempt number and
    Progress History showed duplicate "Attempt #2" cards.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000004")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        s1 = await _open_quiz_page(client, token)
        await _open_quiz_page(client, token)  # reload mid-attempt
        await _finish(client, token, s1["session_id"])

        s2 = await _open_quiz_page(client, token)
        await _finish(client, token, s2["session_id"])

    history = await _history(client, token)
    attempts = sorted(s["attempt_number"] for s in history["sessions"])
    assert attempts == [1, 2], history["sessions"]


# ── Display: stop showing the rows already in the database ────────────────────


@pytest.mark.asyncio
async def test_history_hides_never_answered_sessions(client, db_conn):
    """The 78 rows already on the demo box.

    Inserted directly, because reuse prevents new ones — this is specifically
    the residue that reuse cannot clean up.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000005")
    await _insert_student(client, student_id)

    pool = client._transport.app.state.pool
    for _ in range(6):
        await pool.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, attempt_number, completed)
            VALUES ($1, $2, $3, 8, 'Mathematics', 1, FALSE)
            """,
            uuid.UUID(student_id),
            _UNIT,
            _CURRICULUM,
        )

    history = await _history(client, token)
    assert history["sessions"] == [], history
    assert history["total"] == 0, "the total still counts the hidden rows"


@pytest.mark.asyncio
async def test_history_keeps_an_answered_but_abandoned_session(client, db_conn):
    """Guard against over-correcting.

    A student who answered two questions and walked away did real work. Hiding
    that would lose it — the target is page loads, not unfinished attempts.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000006")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        opened = await _open_quiz_page(client, token)
    await _record_answer_row(client, opened["session_id"])

    history = await _history(client, token)
    ids = [s["session_id"] for s in history["sessions"]]
    assert opened["session_id"] in ids, history


@pytest.mark.asyncio
async def test_history_keeps_completed_sessions(client, db_conn):
    """The obvious one — a finished quiz is always history.

    The score submitted here is ignored: grading is server-side off the Redis
    tally (pitfall #35), and this session has no recorded answers, so 0 is the
    honest result. What matters for #579 is that the row is kept and counted.
    """
    token, student_id = _token_and_id("f5790000-0000-0000-0000-000000000007")
    await _insert_student(client, student_id)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        opened = await _open_quiz_page(client, token)
        await _finish(client, token, opened["session_id"], score=6)

    history = await _history(client, token)
    assert len(history["sessions"]) == 1, history
    assert history["sessions"][0]["session_id"] == opened["session_id"]
    assert history["sessions"][0]["completed"] is True
    assert history["total"] == 1


# ── Counts: stop reporting page loads as attempts ─────────────────────────────


@pytest.mark.asyncio
async def test_overview_quiz_attempts_excludes_page_loads(client, db_conn):
    """Venki's "QUIZ ATTEMPTS 85" on the 30-day Overview.

    `COUNT(*)` over progress_sessions counted every page load. A teacher reading
    85 attempts where 8 quizzes were taken cannot use the number for anything.

    The pass rates in the same query already filter on `completed`, so they were
    never affected — the fix must change what counts as an attempt without
    touching them (see the note on #579: avg score verified correct and must
    stay that way).
    """
    school = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": "Phantom Attempts School",
            "contact_email": "phantomattempts@school.example.com",
            "country": "ZA",
            "password": "SecureTestPwd1!",
        },
    )
    assert school.status_code == 201, school.text
    reg = school.json()

    student_id = str(uuid.uuid4())
    email = f"phantom-{student_id[:8]}@example.com"
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status, school_id)
            VALUES ($1, $2, 'Phantom Counted', $3, 8, 'en', 'active', $4)
            """,
            uuid.UUID(student_id),
            f"auth0|pc-{student_id.replace('-', '')}",
            email,
            uuid.UUID(reg["school_id"]),
        )
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', 8)
            """,
            uuid.UUID(reg["school_id"]),
            email,
            uuid.UUID(student_id),
        )
        # One genuine completed attempt ...
        real_session = await conn.fetchval(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject, started_at, ended_at,
                 score, total_questions, completed, attempt_number, passed)
            VALUES ($1, $2, $3, 8, 'Mathematics', NOW(), NOW(), 7, 8, TRUE, 1, TRUE)
            RETURNING session_id
            """,
            uuid.UUID(student_id),
            _UNIT,
            _CURRICULUM,
        )
        assert real_session is not None
        # ... and nine page loads nobody answered.
        for _ in range(9):
            await conn.execute(
                """
                INSERT INTO progress_sessions
                    (student_id, unit_id, curriculum_id, grade, subject, started_at,
                     completed, attempt_number)
                VALUES ($1, $2, $3, 8, 'Mathematics', NOW(), FALSE, 1)
                """,
                uuid.UUID(student_id),
                _UNIT,
                _CURRICULUM,
            )

    from tests.helpers.token_factory import make_teacher_token

    headers = {
        "Authorization": "Bearer "
        + make_teacher_token(
            teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
        )
    }
    r = await client.get(
        f"/api/v1/reports/school/{reg['school_id']}/overview", headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["quiz_attempts"] == 1, (
        f"quiz_attempts {body['quiz_attempts']} counts page loads (10 = unfiltered)"
    )
    # The pass rate must be untouched by the fix: one first-attempt pass of one.
    assert body["first_attempt_pass_rate_pct"] == 100.0, body
