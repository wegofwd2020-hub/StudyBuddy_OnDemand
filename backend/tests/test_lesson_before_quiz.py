"""A quiz requires the lesson first — product decision, 2026-09-01.

A tester asked: "Current system allows me to take a quiz without going through
the Lesson – Is this OK? Ideally quiz should be enabled if I go through the
lesson fully." The answer is no, it is not OK, and this gate is the result. A
separate revision mode — a "Quiz Book" to drill from — is planned as its own
feature, which is the right home for deliberate quiz-only practice.

The gate is enforced in TWO places and the second is the important one:

  * `POST /progress/session`, because the quiz page opens the session FIRST and
    fetches the quiz for it (#567). Gating only the content endpoint would still
    write a progress_sessions row per blocked attempt, and `attempt_number` is
    COUNT(*) + 1 — so a student bouncing off the gate would inflate their own
    attempt count on a unit they never sat (#465 / #579 all over again).
  * `GET /content/{unit_id}/quiz`, because the backend is the sole authority on
    access and a client can simply not call the session endpoint.

Two ways to pass the gate, and the tests below care more about the second:
opening the unit's content, OR already having an attempt on it. The second is
grandfathering, and it is not a nicety — on the demo, 26 existing sessions across
4 students have no lesson view and 9 of them PASSED. Without it this change
reaches backwards and locks real students out of retrying units they have
already sat.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_student_token

# A SCHOOL-OWNED curriculum, with ids unique to this file.
#
# The first draft used `default-2026-g10`, the second `default-2026-g6`, and both
# collided: several suites seed a shared `default-{year}-g{grade}` and then assert
# how many units it contains, so one extra unit from here changed their answer
# depending on collection order. Every grade from 5 to 12 is already spoken for,
# so there was no free one to move to.
#
# Resolution step 1 is the school's OWN curriculum, so enrolling these students in
# their own school takes this file out of the shared namespace altogether rather
# than hunting for a gap that does not exist.
SCHOOL_ID = "d9000000-0000-0000-0000-0000000000a1"
CUR = "lesson-gate-curriculum"
UNIT = "LGATE-MATH-001"


def _seed(client: AsyncClient, *, lesson: bool = True, quiz: bool = True) -> bool:
    """Put real content on disk. Returns False when the store is not filesystem-backed.

    `lesson` is a parameter because the gate MUST fail open when there is no
    lesson to read — otherwise a unit with a quiz and no lesson is locked forever
    and the student is told to go and read something that does not exist.
    """
    storage = client._transport.app.state.storage
    base = getattr(storage, "_root", None)
    if base is None:
        return False
    unit_dir = os.path.join(str(base), "curricula", CUR, UNIT)
    os.makedirs(unit_dir, exist_ok=True)

    if lesson:
        with open(os.path.join(unit_dir, "lesson_en.json"), "w") as fh:
            json.dump(
                {
                    "unit_id": UNIT,
                    "title": "Linear Equations",
                    "grade": 6,
                    "subject": "Mathematics",
                    "lang": "en",
                    "sections": [{"heading": "Overview", "body": "Body."}],
                    "key_points": ["a"],
                    "model": "test",
                },
                fh,
            )
    else:
        # Absent, not empty — the gate asks whether a lesson EXISTS.
        for name in ("lesson_en.json", "lesson_fr.json"):
            p = os.path.join(unit_dir, name)
            if os.path.exists(p):
                os.remove(p)

    if quiz:
        with open(os.path.join(unit_dir, "quiz_set_1_en.json"), "w") as fh:
            json.dump(
                {
                    "unit_id": UNIT,
                    "set_number": 1,
                    "language": "en",
                    "total_questions": 1,
                    "estimated_duration_minutes": 5,
                    "passing_score": 60,
                    "generated_at": "2026-09-01T00:00:00Z",
                    "model": "test",
                    "content_version": 1,
                    "questions": [
                        {
                            "question_id": "q1",
                            "question_text": "2 + 2 = ?",
                            "question_type": "multiple_choice",
                            "correct_option": "B",
                            "options": [
                                {"option_id": "A", "text": "3"},
                                {"option_id": "B", "text": "4"},
                            ],
                            "explanation": "It is 4.",
                            "difficulty": "easy",
                        }
                    ],
                },
                fh,
            )
    return True


async def _seed_curriculum(client: AsyncClient) -> None:
    """The content resolver reads `curricula` / `curriculum_units`; files on disk
    alone are not enough for it to find the unit."""
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, status)
            VALUES ($1, 'Lesson Gate School', 'lessongate@school.example.com', 'IN', 'active')
            ON CONFLICT (school_id) DO NOTHING
            """,
            uuid.UUID(SCHOOL_ID),
        )
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, grade, year, owner_type, school_id, is_default)
            VALUES ($1, 'Gate Curriculum', 6, 2026, 'school', $2, FALSE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            CUR,
            uuid.UUID(SCHOOL_ID),
        )
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, sort_order)
            VALUES ($1, $2, 'Mathematics', 'Linear Equations', 'Linear Equations', 0)
            ON CONFLICT DO NOTHING
            """,
            UNIT,
            CUR,
        )
        await conn.execute(
            """
            INSERT INTO content_subject_versions
                (curriculum_id, subject, subject_name, version_number, status)
            VALUES ($1, 'Mathematics', 'Mathematics', 1, 'published')
            ON CONFLICT DO NOTHING
            """,
            CUR,
        )


async def _student(client: AsyncClient, grade: int = 6) -> str:
    await _seed_curriculum(client)
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, email, name, grade, locale, school_id)
            VALUES ($1, $2, $3, 'Gate Student', $4, 'en', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|gate-{student_id.replace('-', '')}",
            f"gate-{student_id[:8]}@example.com",
            grade,
            uuid.UUID(SCHOOL_ID),
        )
    return student_id


async def _record_view(client: AsyncClient, student_id: str, unit_id: str = UNIT) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)
            VALUES ($1, $2, $3, 120)
            """,
            uuid.UUID(student_id),
            unit_id,
            CUR,
        )


async def _record_prior_attempt(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (student_id, unit_id, curriculum_id, grade, subject,
                 attempt_number, completed, passed, score, total_questions)
            VALUES ($1, $2, $3, 6, 'Mathematics', 1, TRUE, TRUE, 5, 8)
            """,
            uuid.UUID(student_id),
            UNIT,
            CUR,
        )


def _hdr(student_id: str, grade: int = 6) -> dict:
    return {
        "Authorization": f"Bearer {make_student_token(student_id, grade, school_id=SCHOOL_ID)}"
    }


async def _session_count(client: AsyncClient, student_id: str) -> int:
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetchval(
            "SELECT count(*) FROM progress_sessions WHERE student_id = $1",
            uuid.UUID(student_id),
        )


# ── The gate holds ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quiz_is_refused_before_the_lesson_is_opened(client, db_conn):
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "lesson_required"


@pytest.mark.asyncio
async def test_session_is_refused_before_the_lesson_is_opened(client, db_conn):
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)

    r = await client.post("/api/v1/progress/session", json={"unit_id": UNIT}, headers=_hdr(student_id))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "lesson_required"


@pytest.mark.asyncio
async def test_a_blocked_attempt_creates_no_session_row(client, db_conn):
    """The reason the gate is on the session endpoint at all.

    `attempt_number` is COUNT(*) + 1, so a row written for an attempt that never
    happened permanently inflates the student's attempt count on that unit — and
    it shows up in their history as a phantom never-completed attempt (#465,
    #579). Three refusals must leave zero rows.
    """
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)

    for _ in range(3):
        r = await client.post(
            "/api/v1/progress/session", json={"unit_id": UNIT}, headers=_hdr(student_id)
        )
        assert r.status_code == 403

    assert await _session_count(client, student_id) == 0


# ── The gate opens ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opening_the_lesson_unlocks_the_quiz(client, db_conn):
    """The negative direction for every test above: a gate that refused everyone
    would pass them all while breaking the product completely."""
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)
    await _record_view(client, student_id)

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    assert r.status_code == 200, r.text
    assert r.json()["questions"]

    s = await client.post(
        "/api/v1/progress/session", json={"unit_id": UNIT}, headers=_hdr(student_id)
    )
    assert s.status_code == 201, s.text


@pytest.mark.asyncio
async def test_a_student_with_a_prior_attempt_is_not_locked_out(client, db_conn):
    """Grandfathering, and the test that matters most on release day.

    On the demo alone, 26 existing sessions across 4 students have no lesson view
    and 9 of them PASSED. Without this branch, shipping the gate would retroactively
    stop those students retrying units they have already sat — a rule change that
    reaches backwards, which is indistinguishable from a regression to the person
    it happens to.
    """
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)
    await _record_prior_attempt(client, student_id)  # no lesson view at all

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    assert r.status_code == 200, r.text

    s = await client.post(
        "/api/v1/progress/session", json={"unit_id": UNIT}, headers=_hdr(student_id)
    )
    assert s.status_code == 201, s.text


@pytest.mark.asyncio
async def test_a_unit_with_no_lesson_is_not_locked_forever(client, db_conn):
    """The gate must never make content unreachable.

    A unit with a quiz and no lesson would, under a naive gate, tell the student
    to go and read something that does not exist — permanently. Every quiz-bearing
    unit on the demo currently has a lesson, so this protects against content that
    is partial rather than against a state we are in today.
    """
    if not _seed(client, lesson=False):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    assert r.status_code == 200, r.text

    s = await client.post(
        "/api/v1/progress/session", json={"unit_id": UNIT}, headers=_hdr(student_id)
    )
    assert s.status_code == 201, s.text


@pytest.mark.asyncio
async def test_the_gate_is_per_unit(client, db_conn):
    """Reading one lesson must not unlock every quiz. A gate keyed on the STUDENT
    rather than the (student, unit) pair would pass the unlock test above and be
    worthless."""
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)
    await _record_view(client, student_id, unit_id="LGATE-MATH-999")  # a different unit

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_the_gate_is_per_student(client, db_conn):
    """One student reading the lesson must not unlock the quiz for another."""
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    reader = await _student(client)
    other = await _student(client)
    await _record_view(client, reader)

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(other))
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_the_refusal_says_nothing_technical_to_a_student(client, db_conn):
    """Content Rule #5: no status codes, stack traces or internal identifiers in
    anything a student reads. The message has to say what to DO."""
    if not _seed(client):
        pytest.skip("storage backend is not filesystem-backed")
    student_id = await _student(client)

    r = await client.get(f"/api/v1/content/{UNIT}/quiz", headers=_hdr(student_id))
    msg = r.json()["detail"]
    assert "lesson" in msg.lower()
    for leak in ("403", "forbidden", "curriculum_id", CUR, "sql", "traceback"):
        assert leak.lower() not in msg.lower(), f"student-facing copy leaked {leak!r}"
