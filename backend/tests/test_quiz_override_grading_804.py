"""
tests/test_quiz_override_grading_804.py

#804 — a school override must GRADE, not merely be served.

#529 made serving and grading share one resolver, but they still disagree about
WHICH curriculum id to look an override up under:

  - `unit_content_active_versions` is keyed by the school's FORK id (the approve
    endpoint's path curriculum_id, forced school-owned by
    `_assert_school_owns_curriculum`, school/router.py:3159-3175);
  - serving looks it up under the UNSWAPPED id it resolved for the student —
    the fork (content/router.py:521-523) — and finds it;
  - grading looks it up under `progress_sessions.curriculum_id`, which
    `resolve_unit_curriculum` wrote with the fork→OOB swap already applied
    (progress/router.py:107) — the SOURCE id — and misses, falling through to
    the store.

Net: the student sits the override's questions and is marked against the
platform's answer key. Pitfall #35's `q1…qN` collision, silently.

These tests drive the REAL path — a session opened through the endpoint, so the
recorded curriculum_id is the swapped source one — because a test that calls
`resolve_quiz_answer_key(school, FORK_id, ...)` directly passes while the bug is
present. That is the trap, not the test.
"""

from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app

from src.core.storage import LocalStorage
from tests.helpers.token_factory import make_student_token

_PW = "SecureTestPwd1!"
_GRADE = 8
_OOB_CURRICULUM_ID = "test-oob-g8-804"
_UNIT_ID = "test-oob-g8-804-MATH-U01"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _quiz_body(*, correct: str, text: str) -> dict:
    return {
        "questions": [
            {
                "question_id": "q1",
                "question_text": text,
                "question_type": "multiple_choice",
                "options": [
                    {"option_id": "A", "text": "42"},
                    {"option_id": "B", "text": "36"},
                ],
                "correct_option": correct,
                "explanation": f"{correct} is the answer here.",
            }
        ]
    }


# The platform store says A (index 0). The school's override says B (index 1) —
# so the student's verdict tells you which body graded them. The stems differ
# too, so a `stable_question_id` tells you the same thing.
_STORE_TEXT = "What is 6 x 7?"
_OVERRIDE_TEXT = "What is 7 x 6, in plain words?"
_STORE_BODY = _quiz_body(correct="A", text=_STORE_TEXT)
_OVERRIDE_BODY = _quiz_body(correct="B", text=_OVERRIDE_TEXT)
_STORE_INDEX = 0
_OVERRIDE_INDEX = 1


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def oob_curriculum(client: AsyncClient) -> dict:
    """One platform curriculum + unit, written through the app's own pool so the
    request-handling connections can see it."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO curricula
            (curriculum_id, name, grade, year, is_default,
             owner_type, status, source_type, retention_status)
        VALUES ($1, $2, $3, 2026, TRUE, 'platform', 'active', 'default', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _OOB_CURRICULUM_ID,
        "Grade 8 Math (804 test)",
        _GRADE,
    )
    await pool.execute(
        """
        INSERT INTO curriculum_units
            (unit_id, curriculum_id, subject, title, unit_name, has_lab, sort_order)
        VALUES ($1, $2, 'MATH', 'Multiplication', 'Multiplication', FALSE, 0)
        ON CONFLICT DO NOTHING
        """,
        _UNIT_ID,
        _OOB_CURRICULUM_ID,
    )
    return {"curriculum_id": _OOB_CURRICULUM_ID, "unit_id": _UNIT_ID}


@pytest.fixture()
def quiz_content_store(tmp_path, oob_curriculum):
    """A tmp LocalStorage carrying the unit's lesson + 3 quiz sets (store says A)."""
    unit_dir = tmp_path / "curricula" / _OOB_CURRICULUM_ID / _UNIT_ID
    unit_dir.mkdir(parents=True)
    (unit_dir / "lesson_en.json").write_text(
        json.dumps({"unit_id": _UNIT_ID, "sections": [{"heading": "Times tables", "body": "6x7"}]})
    )
    for n in (1, 2, 3):
        (unit_dir / f"quiz_set_{n}_en.json").write_text(json.dumps(_STORE_BODY))

    old_storage = app.state.storage
    app.state.storage = LocalStorage(root=str(tmp_path))
    yield tmp_path
    app.state.storage = old_storage


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _adopt_and_import(client: AsyncClient, school_id: str, token: str) -> str:
    """Adopt the platform curriculum and import the unit. Returns the fork id."""
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": _OOB_CURRICULUM_ID},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    adoption_id = r.json()["adoption_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{_UNIT_ID}/import",
        headers=_auth(token),
    )
    assert r2.status_code == 201, r2.text
    return r2.json()["forked_curriculum_id"]


async def _adopt_import_and_override_every_set(
    client: AsyncClient, school_id: str, token: str
) -> str:
    """As above, then publish an override for all three quiz sets.

    Every set is overridden so the test does not depend on which set the session
    happens to pin — the rotation is the server's business, not this test's.

    All three drafts are saved BEFORE the single review/approve pass: an import
    bundles its content types under one `bundle_id`, and approving one member
    approves the bundle (`_latest_overrides_for_unit`, school/router.py:2352),
    after which the others are no longer editable.
    """
    fork_id = await _adopt_and_import(client, school_id, token)

    base = f"/api/v1/schools/{school_id}/content/{fork_id}/units/{_UNIT_ID}"
    for n in (1, 2, 3):
        r3 = await client.put(
            f"{base}/overrides/quiz_set_{n}",
            json={"body": _OVERRIDE_BODY, "lang": "en"},
            headers=_auth(token),
        )
        assert r3.status_code == 200, r3.text

    r4 = await client.post(f"{base}/review", json={"lang": "en"}, headers=_auth(token))
    assert r4.status_code == 200, r4.text
    r5 = await client.post(
        f"{base}/approve", json={"lang": "en", "publish": True}, headers=_auth(token)
    )
    assert r5.status_code == 200, r5.text

    return fork_id


async def _student_of(client: AsyncClient, school_id: str) -> tuple[str, str]:
    """A grade-8 student of this school, already past the lesson gate."""
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale,
                 account_status, school_id)
            VALUES ($1, $2, '804 Student', $3, $4, 'en', 'active', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|s804-{student_id.replace('-', '')}",
            f"s804-{student_id[:8]}@example.com",
            _GRADE,
            uuid.UUID(school_id),
        )
        await conn.execute(
            """
            INSERT INTO lesson_views (student_id, unit_id, curriculum_id, duration_s)
            VALUES ($1, $2, $3, 60)
            """,
            uuid.UUID(student_id),
            _UNIT_ID,
            _OOB_CURRICULUM_ID,
        )
    return student_id, make_student_token(student_id=student_id, grade=_GRADE, school_id=school_id)


async def _sit_the_quiz(client: AsyncClient, token: str, *, picked: int) -> dict:
    """Open a session, answer q1 with `picked`, end it. Returns the end body."""
    started = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT_ID, "curriculum_id": "ignored-by-the-server"},
        headers=_auth(token),
    )
    assert started.status_code == 201, started.text
    session_id = started.json()["session_id"]

    answered = await client.post(
        f"/api/v1/progress/session/{session_id}/answer",
        json={"question_id": "q1", "student_answer": picked, "ms_taken": 4000},
        headers=_auth(token),
    )
    assert answered.status_code == 200, answered.text

    ended = await client.post(
        f"/api/v1/progress/session/{session_id}/end",
        json={"score": 0, "total_questions": 1},
        headers=_auth(token),
    )
    assert ended.status_code == 200, ended.text
    return ended.json()


# ── The seam itself ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_session_on_a_fork_records_the_source_curriculum_id(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """Why the override lookup misses: the session does NOT store the fork id.

    Not a bug in itself — the fork has no `curriculum_units` rows, so the swap is
    what makes the unit resolvable at all. It is the premise the grading fix has
    to accommodate, so it is pinned here rather than assumed.
    """
    school = await _register(client, "Seam School 804", "seam-804@example.com")
    fork_id = await _adopt_import_and_override_every_set(
        client, school["school_id"], school["access_token"]
    )
    student_id, token = await _student_of(client, school["school_id"])

    started = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT_ID, "curriculum_id": fork_id},
        headers=_auth(token),
    )
    assert started.status_code == 201, started.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        recorded = await conn.fetchval(
            "SELECT curriculum_id FROM progress_sessions WHERE session_id = $1",
            uuid.UUID(started.json()["session_id"]),
        )
    assert recorded == _OOB_CURRICULUM_ID, recorded
    assert recorded != fork_id
    assert student_id  # the session belongs to the school's own student


# ── What actually grades ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_overrides_answer_is_the_one_that_grades(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The school corrected the answer to B; a student who picks B must score."""
    school = await _register(client, "Graded School 804", "graded-804@example.com")
    await _adopt_import_and_override_every_set(client, school["school_id"], school["access_token"])
    _student, token = await _student_of(client, school["school_id"])

    body = await _sit_the_quiz(client, token, picked=_OVERRIDE_INDEX)

    assert body["score"] == 1, "the school's own answer key must be the one that grades"
    reveal = {r["question_id"]: r for r in body.get("reveal", [])}
    assert reveal["q1"]["correct"] is True
    assert reveal["q1"]["correct_index"] == _OVERRIDE_INDEX


@pytest.mark.asyncio
async def test_the_platform_answer_is_wrong_once_the_school_has_overridden(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The negative case. Without it the fix above could mark everything correct
    and the assertion would still pass."""
    school = await _register(client, "Negative School 804", "negative-804@example.com")
    await _adopt_import_and_override_every_set(client, school["school_id"], school["access_token"])
    _student, token = await _student_of(client, school["school_id"])

    body = await _sit_the_quiz(client, token, picked=_STORE_INDEX)

    assert body["score"] == 0, "the platform's superseded answer must not score"
    reveal = {r["question_id"]: r for r in body.get("reveal", [])}
    assert reveal["q1"]["correct"] is False
    assert reveal["q1"]["correct_index"] == _OVERRIDE_INDEX


@pytest.mark.asyncio
async def test_a_school_without_an_override_still_grades_from_the_store(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The fix must not invent an override where there is none — a school that
    owns a fork but has overridden nothing has to fall through to the store
    exactly as before (#529)."""
    school = await _register(client, "Store School 804", "store-804@example.com")
    await _adopt_and_import(client, school["school_id"], school["access_token"])
    _student, token = await _student_of(client, school["school_id"])

    body = await _sit_the_quiz(client, token, picked=_STORE_INDEX)

    assert body["score"] == 1
    reveal = {r["question_id"]: r for r in body.get("reveal", [])}
    assert reveal["q1"]["correct_index"] == _STORE_INDEX


# ── The same seam on the feedback path ────────────────────────────────────────


@pytest.mark.asyncio
async def test_flagging_a_question_records_the_question_the_student_actually_saw(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """`POST /feedback` narrows to a question by re-resolving the session's key.

    It passed `school_id=None`, which skips the override branch outright — so a
    school whose own copy asks a different question had its students' flags
    recorded against the PLATFORM's question. The count on the answer-review page
    (#762) is then permanently 0 for exactly the schools that edited something.
    """
    from src.core.question_identity import stable_question_id

    school = await _register(client, "Flagging School 804", "flagging-804@example.com")
    await _adopt_import_and_override_every_set(client, school["school_id"], school["access_token"])
    student_id, token = await _student_of(client, school["school_id"])

    started = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT_ID},
        headers=_auth(token),
    )
    assert started.status_code == 201, started.text
    session_id = started.json()["session_id"]

    flagged = await client.post(
        "/api/v1/feedback",
        json={
            "category": "content",
            "unit_id": _UNIT_ID,
            "content_type": "quiz",
            "helpful": False,
            "session_id": session_id,
            "question_id": "q1",
        },
        headers=_auth(token),
    )
    assert flagged.status_code == 200, flagged.text

    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        recorded = await conn.fetchval(
            "SELECT stable_question_id FROM feedback WHERE student_id = $1",
            uuid.UUID(student_id),
        )

    # The id names the QUESTION, and the question the student saw is the
    # school's. It is hashed with the SOURCE curriculum id either way — that is
    # what every other recorded id uses — so only the STEM distinguishes them.
    assert recorded == stable_question_id(_OOB_CURRICULUM_ID, _UNIT_ID, "en", _OVERRIDE_TEXT)
    assert recorded != stable_question_id(_OOB_CURRICULUM_ID, _UNIT_ID, "en", _STORE_TEXT)
