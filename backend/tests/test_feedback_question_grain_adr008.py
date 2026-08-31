"""Feedback can name a QUESTION — ADR-008 Phase 2.

`feedback` was keyed by unit and content type. A student could say "this lesson
wasn't helpful"; nobody could say **"question 4 is wrong."**

That sentence is the highest-value signal in ADR-008. Decision 8's statistics can
tell you a question behaves oddly — strong students missing it more often than
weak ones means broken, not hard — but a statistic needs a few dozen responses
first, and can never say why. A person who just read the question can, on the
first encounter.

The client sends the POSITIONAL id it was shown plus its session; the server
resolves the stable identity from the set that session was graded against. These
tests cover both halves of that: the resolution works, and the client cannot use
it to point at a question it was never served.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.core.question_identity import stable_question_id
from tests.helpers.token_factory import make_student_token

CUR = "default-2026-g10"
UNIT = "G10-MATH-001"


STEM = "Which of the following is a prime number?"


def _seed_quiz(client: AsyncClient) -> bool:
    """Put a real quiz set on disk so resolution CAN succeed.

    Without this, every resolution fails for want of content and a test asserting
    None passes for the wrong reason — which is exactly what the ownership test
    did before this helper existed.

    Returns False when the backend is not filesystem-backed, so callers skip
    rather than assert against a store they cannot seed.
    """
    import json
    import os

    storage = client._transport.app.state.storage
    base = getattr(storage, "_root", None)
    if base is None:
        return False

    body = {
        "unit_id": UNIT,
        "set_number": 1,
        "language": "en",
        "total_questions": 1,
        "estimated_duration_minutes": 5,
        "passing_score": 60,
        "generated_at": "2026-08-31T00:00:00Z",
        "model": "test",
        "content_version": 1,
        "questions": [
            {
                "question_id": "q1",
                "question_text": STEM,
                "question_type": "multiple_choice",
                "correct_option": "B",
                "options": [
                    {"option_id": "A", "text": "4"},
                    {"option_id": "B", "text": "7"},
                ],
                "explanation": "7 is prime.",
                "difficulty": "easy",
            }
        ],
    }
    unit_dir = os.path.join(str(base), "curricula", CUR, UNIT)
    os.makedirs(unit_dir, exist_ok=True)
    with open(os.path.join(unit_dir, "quiz_set_1_en.json"), "w") as fh:
        json.dump(body, fh)
    return True


async def _student(client: AsyncClient, grade: int = 10) -> str:
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students (student_id, external_auth_id, email, name, grade, locale)
            VALUES ($1, $2, $3, 'Feedback Student', $4, 'en')
            """,
            uuid.UUID(student_id),
            f"auth0|fbq-{student_id.replace('-', '')}",
            f"fbq-{student_id[:8]}@example.com",
            grade,
        )
    return student_id


async def _session(client: AsyncClient, student_id: str) -> str:
    sid = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, quiz_set)
            VALUES ($1, $2, $3, $4, 10, 'Mathematics', 1, FALSE, 1)
            """,
            uuid.UUID(sid),
            uuid.UUID(student_id),
            UNIT,
            CUR,
        )
    return sid


def _hdr(student_id: str, grade: int = 10) -> dict:
    return {"Authorization": f"Bearer {make_student_token(student_id, grade)}"}


async def _row(client: AsyncClient, feedback_id: str):
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetchrow(
            "SELECT unit_id, stable_question_id FROM feedback WHERE feedback_id = $1",
            uuid.UUID(feedback_id),
        )


# ── The pair is validated ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_question_without_its_session_is_rejected(client, db_conn):
    """Half a pair cannot be resolved, and silently dropping it would record
    feedback the student believes is attached to a question, attached to nothing."""
    student_id = await _student(client)
    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(student_id),
        json={"category": "content", "message": "Q2 is ambiguous", "question_id": "q2"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_a_session_without_a_question_is_rejected(client, db_conn):
    student_id = await _student(client)
    sid = await _session(client, student_id)
    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(student_id),
        json={"category": "content", "message": "something", "session_id": sid},
    )
    assert r.status_code == 422, r.text


# ── Existing feedback keeps working ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_feedback_without_a_question_still_submits(client, db_conn):
    """Most feedback has no question to point at — a lesson thumbs-down has none.
    The narrowing is optional and every existing path is untouched."""
    student_id = await _student(client)
    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(student_id),
        json={
            "category": "content",
            "unit_id": UNIT,
            "content_type": "lesson",
            "helpful": False,
        },
    )
    assert r.status_code == 200, r.text
    row = await _row(client, r.json()["feedback_id"])
    assert row["stable_question_id"] is None


# ── The client cannot name a question it was not served ───────────────────────


@pytest.mark.asyncio
async def test_feedback_cannot_be_attached_to_another_students_session(client, db_conn):
    """Without an ownership check, any student could attach a comment to any
    session by guessing a UUID. The submission still succeeds — the student wrote
    something real — but it is NOT narrowed to the other student's question."""
    if not _seed_quiz(client):
        pytest.skip("storage backend is not filesystem-backed in this environment")
    owner = await _student(client)
    attacker = await _student(client)
    sid = await _session(client, owner)

    # Content is on disk and the session is real, so resolution WOULD succeed.
    # The only thing standing between the attacker and another student's question
    # is the ownership check — which is what this asserts.

    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(attacker),
        json={
            "category": "content",
            "message": "pointing at someone else's session",
            "session_id": sid,
            "question_id": "q1",
        },
    )
    assert r.status_code == 200, r.text
    row = await _row(client, r.json()["feedback_id"])
    assert row["stable_question_id"] is None, (
        "another student's session must not resolve to a question id"
    )


@pytest.mark.asyncio
async def test_an_unknown_question_id_resolves_to_nothing(client, db_conn):
    """A positional id outside the served set names nothing. The comment is kept
    — losing what a student wrote is worse than storing it unnarrowed."""
    if not _seed_quiz(client):
        pytest.skip("storage backend is not filesystem-backed in this environment")
    student_id = await _student(client)
    sid = await _session(client, student_id)

    # q1 exists in the seeded set; q999 does not. So the None below is caused by
    # the id being absent from the set, not by the set being absent.
    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(student_id),
        json={
            "category": "content",
            "message": "q999 does not exist",
            "session_id": sid,
            "question_id": "q999",
        },
    )
    assert r.status_code == 200, r.text
    row = await _row(client, r.json()["feedback_id"])
    assert row["stable_question_id"] is None


# ── Resolution, against real content ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_flag_resolves_to_the_questions_stable_identity(client, db_conn, tmp_path):
    """The whole point: a comment about q1 is stored against the QUESTION, so it
    sits alongside the answers recorded for that same question reached via
    another set."""
    if not _seed_quiz(client):
        pytest.skip("storage backend is not filesystem-backed in this environment")
    student_id = await _student(client)
    sid = await _session(client, student_id)
    stem = STEM

    r = await client.post(
        "/api/v1/feedback",
        headers=_hdr(student_id),
        json={
            "category": "content",
            "message": "This question is ambiguous — two options look prime.",
            "session_id": sid,
            "question_id": "q1",
        },
    )
    assert r.status_code == 200, r.text
    row = await _row(client, r.json()["feedback_id"])
    assert row["stable_question_id"] == stable_question_id(CUR, UNIT, "en", stem), (
        "the flag must land on the question's own identity, not its slot"
    )
