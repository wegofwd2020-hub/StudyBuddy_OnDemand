"""
tests/test_resume_quiz_answers_667.py

A refresh mid-quiz restores what the student had already picked (issue #667).

Venki 2026-08-28:

    "If I click the refresh button in the quiz page after answering the
     questions answers made till the refresh is getting cleared - Is this OK?"

No — though it never affected marking. The answers are graded server-side as
they are given (#506) and a refresh resumes the same attempt with the same
question set (#646); the page simply could not read them back, so a student saw
an empty quiz and re-answered questions they had already done, unable to tell
which.

## What is returned, and what is not

ONLY the option the student picked. Never whether it was correct: the player
withholds the reveal until the summary (#532), and a resume must not become a
way around that. #684 tracks the related hole where the per-answer response
already leaks the key — this endpoint deliberately does not widen it.

## Where it reads from

The Redis tally, not `progress_answers`. Answer writes are fire-and-forget, so
the rows may not exist yet — the same reason `end_session` reads the tally
(pitfall #35). The tally field is now `"<verdict>:<index>"`; the pre-#667 form
was a bare `"1"`/`"0"`, which still scores correctly but carries no index to
restore, so those questions are omitted rather than guessed at.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.core.cache_keys import quiz_answers_key
from src.progress.service import read_answered, read_tally, tally_answer
from tests.helpers.token_factory import make_student_token

_GRADE = 8


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _student(client: AsyncClient) -> str:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status)
            VALUES ($1, $2, 'Resume Student', $3, $4, 'en', 'active')
            """,
            uuid.UUID(student_id),
            f"auth0|resume-{student_id.replace('-', '')}",
            f"resume-{student_id[:8]}@example.com",
            _GRADE,
        )
    return student_id


async def _session(client: AsyncClient, student_id: str) -> str:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return str(
            await conn.fetchval(
                """
                INSERT INTO progress_sessions
                    (student_id, unit_id, curriculum_id, grade, subject, started_at,
                     completed, attempt_number)
                VALUES ($1, 'RES-1', 'default-2026-g8', $2, 'Resume', NOW(), FALSE, 1)
                RETURNING session_id
                """,
                uuid.UUID(student_id),
                _GRADE,
            )
        )


# ── The tally now carries the picked index ────────────────────────────────────


@pytest.mark.asyncio
async def test_the_tally_records_which_option_was_picked(fake_redis):
    await tally_answer(fake_redis, session_id="s1", question_id="q1", correct=True, answer_index=2)

    assert await read_answered(fake_redis, "s1") == {"q1": 2}


@pytest.mark.asyncio
async def test_scoring_is_unchanged_by_the_new_field_shape(fake_redis):
    """The verdict still drives the score — that is what end_session reads."""
    await tally_answer(fake_redis, session_id="s2", question_id="q1", correct=True, answer_index=0)
    await tally_answer(fake_redis, session_id="s2", question_id="q2", correct=False, answer_index=3)

    assert await read_tally(fake_redis, "s2") == 1


@pytest.mark.asyncio
async def test_a_legacy_field_still_scores_but_restores_nothing(fake_redis):
    """Sessions in flight when this shipped carry a bare "1"/"0".

    They must keep scoring correctly; they simply have no index, and a guess
    would show the student an answer they never gave.
    """
    key = quiz_answers_key("s3")
    await fake_redis.hset(key, "q1", "1")
    await fake_redis.hset(key, "q2", "0")

    assert await read_tally(fake_redis, "s3") == 1
    assert await read_answered(fake_redis, "s3") == {}


@pytest.mark.asyncio
async def test_re_answering_overwrites_the_restored_index(fake_redis):
    """Skip-and-return (#532) means the LAST pick is the one to restore."""
    await tally_answer(fake_redis, session_id="s4", question_id="q1", correct=False, answer_index=1)
    await tally_answer(fake_redis, session_id="s4", question_id="q1", correct=True, answer_index=0)

    assert await read_answered(fake_redis, "s4") == {"q1": 0}
    assert await read_tally(fake_redis, "s4") == 1


# ── The endpoint ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_endpoint_returns_picked_options_and_no_verdicts(client, db_conn):
    """The reported case, and the constraint on fixing it."""
    student = await _student(client)
    session_id = await _session(client, student)

    redis = client._transport.app.state.redis
    await tally_answer(
        redis, session_id=session_id, question_id="q1", correct=True, answer_index=2
    )
    await tally_answer(
        redis, session_id=session_id, question_id="q2", correct=False, answer_index=0
    )

    token = make_student_token(student_id=student, grade=_GRADE)
    r = await client.get(
        f"/api/v1/progress/session/{session_id}/answers", headers=_auth(token)
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["answers"] == [
        {"question_id": "q1", "answer_index": 2},
        {"question_id": "q2", "answer_index": 0},
    ], body
    # The reveal stays with the summary (#532) — no verdict may appear here.
    assert "correct" not in r.text, r.text


@pytest.mark.asyncio
async def test_another_students_session_is_refused(client, db_conn):
    """A session id is not a capability."""
    owner = await _student(client)
    intruder = await _student(client)
    session_id = await _session(client, owner)

    token = make_student_token(student_id=intruder, grade=_GRADE)
    r = await client.get(
        f"/api/v1/progress/session/{session_id}/answers", headers=_auth(token)
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_an_unanswered_session_returns_an_empty_list(client, db_conn):
    """Not an error — a student who refreshes before answering has nothing yet."""
    student = await _student(client)
    session_id = await _session(client, student)

    token = make_student_token(student_id=student, grade=_GRADE)
    r = await client.get(
        f"/api/v1/progress/session/{session_id}/answers", headers=_auth(token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["answers"] == [], r.json()
