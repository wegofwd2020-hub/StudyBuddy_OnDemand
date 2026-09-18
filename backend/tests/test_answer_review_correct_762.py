"""
tests/test_answer_review_correct_762.py

Task 4 (#762) — POST .../answers/{stable_question_id}/correct

Changes WHICH option is correct for one question, in the school's own copy,
creating that copy (adoption -> fork -> import) when the school has none.

Every ownership case ends by asserting the corrected answer is **served and
graded through a real session**, not that a row was written. A test that calls
`resolve_quiz_answer_key(school, FORK_id, ...)` directly passes even when the
correction never reaches grading (#804), and a test that only reads the row back
passes even when the L2 override cache hides it for an hour (#806). Both were
live bugs in this feature's own dependencies, so both are asserted against here
the way `test_quiz_override_grading_804.py` does: open a session through the
endpoint, answer, read the verdict.

The pre-correction sit is load-bearing in cases 1 and 2, not scene-setting: it
is what puts the OLD answer (case 1) or the miss sentinel (case 2) into Redis.
Remove it and the tests still pass with the cache invalidation deleted.

Fixtures come from test_answer_review_list_762 rather than being re-declared —
list, validate and correct all resolve a question through the same path, and a
second, subtly different fixture would let them drift apart unnoticed.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.core.question_identity import stable_question_id
from tests.helpers.token_factory import make_student_token, make_teacher_token
from tests.test_answer_review_list_762 import (
    _OOB_CURRICULUM_ID,
    _STORE_BODY,
    _UNIT_ID,
    _answers_url,
    _auth,
    _register,
    oob_curriculum,  # noqa: F401 — imported to REGISTER the fixture
    quiz_content_store,  # noqa: F401 — same
)

_GRADE = 8
_STEM = "What is 6 x 7?"

# The store says A ("42", index 0). Every correction here moves it to B ("36",
# index 1), so a student's verdict says which body graded them.
_STORE_OPTION = "A"
_NEW_OPTION = "B"
_STORE_INDEX = 0
_NEW_INDEX = 1
_STORE_TEXT = "42"
_NEW_TEXT = "36"

# A second unit, used only to give a school a fork WITHOUT importing the unit
# under test — the literal "owns a fork but no override for this unit" case.
_SECOND_UNIT_ID = f"{_OOB_CURRICULUM_ID}-MATH-U02"


def _stable_id(stem: str = _STEM) -> str:
    """The id the GRADER mints: source curriculum, unit, the language the file
    was actually read in."""
    return stable_question_id(_OOB_CURRICULUM_ID, _UNIT_ID, "en", stem)


def _correct_url(school_id: str, curriculum_id: str, stable_id: str) -> str:
    return (
        f"/api/v1/schools/{school_id}/content/{curriculum_id}"
        f"/units/{_UNIT_ID}/answers/{stable_id}/correct"
    )


def _pool(client: AsyncClient):
    return client._transport.app.state.pool


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def second_unit(client: AsyncClient, quiz_content_store):  # noqa: F811
    """A second unit of the same platform curriculum, with quiz content.

    Importing THIS unit is how a school ends up owning a fork while the unit
    under test has no override of any kind — case 2 as the design states it.
    """
    pool = _pool(client)
    await pool.execute(
        """
        INSERT INTO curriculum_units
            (unit_id, curriculum_id, subject, title, unit_name, has_lab, sort_order)
        VALUES ($1, $2, 'MATH', 'Division', 'Division', FALSE, 1)
        ON CONFLICT DO NOTHING
        """,
        _SECOND_UNIT_ID,
        _OOB_CURRICULUM_ID,
    )
    unit_dir = quiz_content_store / "curricula" / _OOB_CURRICULUM_ID / _SECOND_UNIT_ID
    unit_dir.mkdir(parents=True, exist_ok=True)
    for n in (1, 2, 3):
        (unit_dir / f"quiz_set_{n}_en.json").write_text(json.dumps(_STORE_BODY))
    return _SECOND_UNIT_ID


# ── Ownership set-up helpers ──────────────────────────────────────────────────


async def _adopt(client: AsyncClient, school_id: str, token: str) -> str:
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": _OOB_CURRICULUM_ID},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["adoption_id"]


async def _import(
    client: AsyncClient, school_id: str, token: str, adoption_id: str, unit_id: str
) -> str:
    r = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{unit_id}/import",
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["forked_curriculum_id"]


async def _publish_imported(client: AsyncClient, school_id: str, token: str, fork_id: str) -> None:
    """Approve + publish the imported bodies UNCHANGED.

    The result is ownership "override" whose answer is still the platform's "A",
    which is the state a correction has to supersede — and, once a student has
    sat the quiz, the state that is sitting in the L2 cache.
    """
    base = f"/api/v1/schools/{school_id}/content/{fork_id}/units/{_UNIT_ID}"
    r = await client.post(f"{base}/review", json={"lang": "en"}, headers=_auth(token))
    assert r.status_code == 200, r.text
    r2 = await client.post(
        f"{base}/approve", json={"lang": "en", "publish": True}, headers=_auth(token)
    )
    assert r2.status_code == 200, r2.text


async def _student_of(
    client: AsyncClient,
    school_id: str,
    *,
    token: str | None = None,
    package: str | None = None,
) -> tuple[str, str]:
    """A grade-8 student of this school, already past the lesson gate.

    `package` wires the student through a CLASSROOM PACKAGE instead of a
    school-owned curriculum — the demo's actual shape (design doc: classroom
    packages bypass adoption entirely), and the only way a student reaches a
    curriculum their school has not adopted.
    """
    student_id = str(uuid.uuid4())
    pool = _pool(client)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale,
                 account_status, school_id)
            VALUES ($1, $2, '762 Student', $3, $4, 'en', 'active', $5)
            """,
            uuid.UUID(student_id),
            f"auth0|s762-{student_id.replace('-', '')}",
            f"s762-{student_id[:8]}@example.com",
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

    if package:
        assert token, "wiring a classroom package needs a school_admin token"
        r = await client.post(
            f"/api/v1/schools/{school_id}/classrooms",
            json={"name": "762 Class", "grade": _GRADE},
            headers=_auth(token),
        )
        assert r.status_code == 201, r.text
        classroom_id = r.json()["classroom_id"]
        r2 = await client.post(
            f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/packages",
            json={"curriculum_id": package},
            headers=_auth(token),
        )
        assert r2.status_code == 204, r2.text
        r3 = await client.post(
            f"/api/v1/schools/{school_id}/classrooms/{classroom_id}/students",
            json={"student_id": student_id},
            headers=_auth(token),
        )
        assert r3.status_code == 204, r3.text

    return student_id, make_student_token(student_id=student_id, grade=_GRADE, school_id=school_id)


async def _warm_the_override_cache(client: AsyncClient, school_id: str) -> None:
    """Resolve the answer key for EVERY quiz set, exactly as grading does.

    `get_active_override` caches a JSON-null miss sentinel — or the body that is
    active right now — for an hour. A session pins ONE set
    (`pin_session_quiz_set`, rotation per attempt), so sitting the quiz warms
    only that set's key and the NEXT sit rotates onto a cold one. That made the
    #806 assertion pass against the unfixed code: the second sit read a key
    nothing had cached. Warming all three is what makes "the cache is stale"
    the only remaining explanation for a wrong verdict.
    """
    from src.content.service import resolve_quiz_answer_key

    state = client._transport.app.state
    for set_number in (1, 2, 3):
        # The SOURCE curriculum id, because that is the id grading holds
        # (`progress_sessions.curriculum_id` is written swapped, #804).
        await resolve_quiz_answer_key(
            school_id,
            _OOB_CURRICULUM_ID,
            _UNIT_ID,
            set_number,
            "en",
            state.pool,
            state.redis,
            state.storage,
        )


async def _sit_the_quiz(client: AsyncClient, token: str, *, picked: int) -> dict:
    """Open a session through the endpoint, answer q1, end it.

    Through the endpoint on purpose: `progress_sessions.curriculum_id` is then
    the SWAPPED source id, which is what grading actually holds (#804).
    """
    started = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": _UNIT_ID},
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


# ── Row readers ───────────────────────────────────────────────────────────────


async def _school_rows(client: AsyncClient, school_id: str) -> dict:
    pool = _pool(client)
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        adoptions = await conn.fetch(
            "SELECT adoption_id, curriculum_id, forked_curriculum_id "
            "FROM school_adopted_curricula WHERE school_id = $1::uuid",
            school_id,
        )
        forks = await conn.fetch(
            "SELECT curriculum_id, source_curriculum_id FROM curricula "
            "WHERE school_id = $1::uuid AND owner_type = 'school'",
            school_id,
        )
        overrides = await conn.fetch(
            "SELECT override_id, content_type, review_status, version_number, body "
            "FROM unit_content_overrides WHERE school_id = $1::uuid AND unit_id = $2 "
            "ORDER BY content_type, version_number",
            school_id,
            _UNIT_ID,
        )
        active = await conn.fetch(
            "SELECT content_type, override_id FROM unit_content_active_versions "
            "WHERE school_id = $1::uuid AND unit_id = $2",
            school_id,
            _UNIT_ID,
        )
        grade_rows = await conn.fetch(
            "SELECT grade, curriculum_id FROM grade_curriculum_assignments "
            "WHERE school_id = $1::uuid",
            school_id,
        )
        validations = await conn.fetch(
            "SELECT stable_question_id, correct_text, validated_by::text AS validated_by "
            "FROM question_validations WHERE school_id = $1::uuid",
            school_id,
        )
    return {
        "adoptions": [dict(r) for r in adoptions],
        "forks": [dict(r) for r in forks],
        "overrides": [dict(r) for r in overrides],
        "active": [dict(r) for r in active],
        "grades": [dict(r) for r in grade_rows],
        "validations": [dict(r) for r in validations],
    }


async def _provision_teacher(
    client: AsyncClient,
    school_id: str,
    admin_token: str,
    email: str,
    capabilities: list[str],
) -> str:
    """A REAL `teachers` row holding `capabilities`.

    Real, not a token over an invented uuid, and that matters for the NEGATIVE
    permission test as much as the positive one. This endpoint writes
    `adopted_by`, `last_edited_by`, `activated_by` and `validated_by` — all FKs
    to `teachers` — and answers a violation of any of them with 403 "please sign
    in again". So a refusal against an invented teacher id is 403 whatever the
    guard is, and the test would pass at either tier: the exact false pass the
    commission-only case exists to rule out. (Caught by mutation: swapping
    `require_review` for `require_curriculum_view` left all 17 tests green until
    this fixture was made real.)
    """
    from unittest.mock import AsyncMock

    with patch("src.email.service.send_welcome_teacher_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Teacher", "email": email},
            headers=_auth(admin_token),
        )
    assert r.status_code == 201, r.text
    teacher_id = r.json()["teacher_id"]

    r2 = await client.put(
        f"/api/v1/schools/{school_id}/teachers/{teacher_id}/capabilities",
        json={"capabilities": capabilities},
        headers=_auth(admin_token),
    )
    assert r2.status_code == 200, r2.text
    return teacher_id


# ── Case 1: an active override already exists ─────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_case_override_the_corrected_answer_is_served_and_graded(
    client: AsyncClient, db_conn
) -> None:
    """The school already has its own copy; the correction is a new version of it.

    The pre-correction sit caches the OLD override body under the fork id for an
    hour. Without invalidation the student keeps being graded against it, which
    is the whole of #806 wearing the correction path's clothes.
    """
    school = await _register(client, "Corr Override School", "corr-ovr-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    adoption_id = await _adopt(client, school_id, token)
    fork_id = await _import(client, school_id, token, adoption_id, _UNIT_ID)
    await _publish_imported(client, school_id, token, fork_id)

    _student, student_token = await _student_of(client, school_id)
    before = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert before["score"] == 0, "B is wrong until the school corrects it"
    await _warm_the_override_cache(client, school_id)

    r = await client.post(
        _correct_url(school_id, fork_id, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": False},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ownership_before"] == "override"
    assert body["created"] == {"adoption": False, "fork": False, "import": False}
    assert body["grade_repointed"] is False
    assert body["override_id"]

    after = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert after["score"] == 1, "the corrected answer must be the one that grades"
    reveal = {q["question_id"]: q for q in after.get("reveal", [])}
    assert reveal["q1"]["correct_index"] == _NEW_INDEX


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_the_superseded_answer_stops_grading(client: AsyncClient, db_conn) -> None:
    """The negative control: without it, a fix that marks everything correct
    passes the test above."""
    school = await _register(client, "Corr Negative School", "corr-neg-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    adoption_id = await _adopt(client, school_id, token)
    fork_id = await _import(client, school_id, token, adoption_id, _UNIT_ID)
    await _publish_imported(client, school_id, token, fork_id)

    r = await client.post(
        _correct_url(school_id, fork_id, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": False},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    _student, student_token = await _student_of(client, school_id)
    body = await _sit_the_quiz(client, student_token, picked=_STORE_INDEX)
    assert body["score"] == 0, "the platform's superseded answer must not score"


# ── Case 2: a fork, but no override for this unit ─────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_case_fork_imports_the_unit_then_corrects_and_grades(
    client: AsyncClient, db_conn, second_unit
) -> None:
    """The school owns a fork (it imported a DIFFERENT unit) but has nothing for
    this one — so the correction has to import it first.

    The pre-correction sit caches the miss sentinel under the FORK id, which is
    the key the correction's override lands on. Without invalidation the student
    is still graded from the store afterwards.
    """
    school = await _register(client, "Corr Fork School", "corr-fork-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    adoption_id = await _adopt(client, school_id, token)
    fork_id = await _import(client, school_id, token, adoption_id, second_unit)

    _student, student_token = await _student_of(client, school_id)
    before = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert before["score"] == 0
    await _warm_the_override_cache(client, school_id)

    r = await client.post(
        _correct_url(school_id, fork_id, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": False},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ownership_before"] == "fork"
    assert body["created"]["adoption"] is False
    assert body["created"]["fork"] is False, "the fork already existed"
    assert body["created"]["import"] is True, "this unit had to be imported"
    assert body["grade_repointed"] is False, "the grade was already pointed at the fork"

    after = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert after["score"] == 1


# ── Case 3: no adoption at all (the demo's case) ──────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_case_none_without_confirmation_is_refused_and_writes_nothing(
    client: AsyncClient, db_conn
) -> None:
    """Forking is a consequence, not a detail: the unit stops tracking platform
    regeneration and the whole grade is repointed. It is refused until the
    reviewer says so, with a reason a client can branch on.

    Carries its own positive control — the same call with `confirm_fork: true`
    must succeed, or "refused" would also describe an unimplemented endpoint.
    """
    school = await _register(client, "Corr None School", "corr-none-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": False},
        headers=_auth(token),
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "fork_confirmation_required"

    rows = await _school_rows(client, school_id)
    assert rows["adoptions"] == []
    assert rows["forks"] == []
    assert rows["overrides"] == []
    assert rows["validations"] == []

    ok = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_case_none_creates_adoption_fork_and_import_exactly_once_and_repoints_the_grade(
    client: AsyncClient, db_conn
) -> None:
    """The demo's case end to end.

    `grade_curriculum_assignments` is asserted explicitly because creating the
    fork repoints the WHOLE grade (import_unit_content), so "correct one answer"
    changes what every student of that grade resolves to. The response says so
    via `grade_repointed`; the row is what makes that claim true.
    """
    school = await _register(client, "Corr Adopt School", "corr-adopt-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _student, student_token = await _student_of(
        client, school_id, token=token, package=_OOB_CURRICULUM_ID
    )
    before = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert before["score"] == 0
    await _warm_the_override_cache(client, school_id)

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ownership_before"] == "none"
    assert body["created"] == {"adoption": True, "fork": True, "import": True}
    assert body["grade_repointed"] is True

    rows = await _school_rows(client, school_id)
    assert len(rows["adoptions"]) == 1, "exactly one adoption"
    assert len(rows["forks"]) == 1, "exactly one fork"
    fork_id = rows["forks"][0]["curriculum_id"]
    assert rows["adoptions"][0]["forked_curriculum_id"] == fork_id
    assert rows["forks"][0]["source_curriculum_id"] == _OOB_CURRICULUM_ID
    assert [(g["grade"], g["curriculum_id"]) for g in rows["grades"]] == [(_GRADE, fork_id)]

    after = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert after["score"] == 1, "the corrected answer must reach the student"


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_second_correction_in_the_same_curriculum_needs_no_confirmation(
    client: AsyncClient, db_conn
) -> None:
    """Design ruling: the confirmation is per curriculum, not per question — a
    reviewer fixing four answers in a unit should not confirm four times."""
    school = await _register(client, "Corr Twice School", "corr-twice-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    first = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _STORE_OPTION, "confirm_fork": False},
        headers=_auth(token),
    )
    assert second.status_code == 200, second.text
    assert second.json()["ownership_before"] == "override"
    assert second.json()["created"] == {"adoption": False, "fork": False, "import": False}


# ── What the correction writes ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_every_set_the_question_appears_in_is_corrected(client: AsyncClient, db_conn) -> None:
    """One `stable_question_id` spans quiz sets (the hash covers the stem, not
    the set number), so a unit holds several BODIES for one question.

    Ruling: a correction fixes the answer in EVERY set the question appears in.
    The set a student sits is picked by the server's rotation, so correcting
    only the set the reviewer happened to be shown would leave the same question
    misgraded on the next attempt — and the grading assertion above could not be
    stated at all.
    """
    school = await _register(client, "Corr Sets School", "corr-sets-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert sorted(r.json()["sets_corrected"]) == [1, 2, 3]

    listing = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert listing.status_code == 200, listing.text
    questions = listing.json()["questions"]
    assert len(questions) == 3
    for q in questions:
        assert q["correct_option"] == _NEW_OPTION, q["set_number"]
        assert q["served_from"] == "override", q["set_number"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_correcting_revalidates_the_question(client: AsyncClient, db_conn) -> None:
    """Design §2: "A correction re-validates automatically, by the reviewer who
    made it." The snapshot must be the NEW answer's text, or the tick it writes
    would read stale the moment it is written."""
    school = await _register(client, "Corr Revalidate School", "corr-reval-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    rows = await _school_rows(client, school_id)
    assert len(rows["validations"]) == 1
    assert rows["validations"][0]["stable_question_id"] == _stable_id()
    assert rows["validations"][0]["correct_text"] == _NEW_TEXT
    assert rows["validations"][0]["validated_by"] == school["teacher_id"]

    listing = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert listing.status_code == 200, listing.text
    for q in listing.json()["questions"]:
        assert q["validated"] is not None, q["set_number"]
        assert q["validated"]["stale"] is False, q["set_number"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_the_new_body_differs_only_in_that_questions_correct_option(
    client: AsyncClient, db_conn
) -> None:
    """A correction changes WHICH option is correct and nothing else — editing
    question or option TEXT stays in the unit editor (design §1 ruling)."""
    school = await _register(client, "Corr Body School", "corr-body-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    rows = await _school_rows(client, school_id)
    active_ids = {a["override_id"] for a in rows["active"]}
    corrected = [
        o
        for o in rows["overrides"]
        if o["override_id"] in active_ids and "quiz" in o["content_type"]
    ]
    assert len(corrected) == 3
    for row in corrected:
        body = row["body"] if isinstance(row["body"], dict) else json.loads(row["body"])
        expected = json.loads(json.dumps(_STORE_BODY))
        expected["questions"][0]["correct_option"] = _NEW_OPTION
        assert body == expected
        assert row["review_status"] == "approved"


# ── Refusals ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_an_option_that_is_not_in_the_question_is_422_and_writes_nothing(
    client: AsyncClient, db_conn
) -> None:
    """`correct_option: "Z"` beside options A and B is the defect this page
    exists to find — writing one would be creating it. Carries a positive
    control so it cannot pass against an unimplemented route."""
    school = await _register(client, "Corr Option School", "corr-opt-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": "Z", "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invalid_option"

    rows = await _school_rows(client, school_id)
    assert rows["adoptions"] == [], "a refused correction must not adopt anything"
    assert rows["forks"] == []
    assert rows["overrides"] == []

    ok = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_an_unknown_question_id_is_404_and_writes_nothing(
    client: AsyncClient, db_conn
) -> None:
    """`stable_question_id` is a hash the caller supplies and no FK can reject
    it. The 404 must be THIS endpoint's structured refusal, not the router's
    bare one — otherwise it is also true of a route that does not exist."""
    school = await _register(client, "Corr Unknown School", "corr-unk-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    ok = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert ok.status_code == 200, ok.text

    absent = _stable_id("A question that is in no set of this unit")
    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, absent),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not_found"

    rows = await _school_rows(client, school_id)
    assert [v["stable_question_id"] for v in rows["validations"]] == [_stable_id()]


# ── Permissions ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_commission_only_teacher_is_refused(client: AsyncClient, db_conn) -> None:
    """The case that tells the two guards apart.

    A teacher with NO capability is refused by `require_curriculum_view` as well,
    so "a plain teacher is refused" passes at either tier. `curriculum.commission`
    clears the view gate and not the review gate — and the same token is asserted
    to still be able to LOOK, which is what makes the refusal a statement about
    the tier rather than about the token.
    """
    school = await _register(client, "Corr Comm School", "corr-comm-762@example.com")
    school_id, admin = school["school_id"], school["access_token"]
    teacher_id = await _provision_teacher(
        client, school_id, admin, "corr-comm-t-762@example.com", ["curriculum.commission"]
    )
    token = make_teacher_token(
        teacher_id=teacher_id,
        school_id=school_id,
        role="teacher",
        capabilities=["curriculum.commission"],
    )

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 403, r.text

    rows = await _school_rows(client, school_id)
    assert rows["adoptions"] == []
    assert rows["forks"] == []

    r2 = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_curriculum_review_teacher_succeeds(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Corr Rev School", "corr-rev-762@example.com")
    school_id, admin = school["school_id"], school["access_token"]
    teacher_id = await _provision_teacher(
        client, school_id, admin, "corr-rev-t-762@example.com", ["curriculum.review"]
    )
    token = make_teacher_token(
        teacher_id=teacher_id,
        school_id=school_id,
        role="teacher",
        capabilities=["curriculum.review"],
    )

    r = await client.post(
        _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    rows = await _school_rows(client, school_id)
    assert rows["validations"][0]["validated_by"] == teacher_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_school_admin_succeeds(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Corr Admin School", "corr-admin-762@example.com")

    r = await client.post(
        _correct_url(school["school_id"], _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(school["access_token"]),  # the founder token is school_admin
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_reviewer_from_another_school_is_refused(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Corr Owner School", "corr-owner-762@example.com")
    outsider = make_teacher_token(school_id=str(uuid.uuid4()), role="school_admin")

    r = await client.post(
        _correct_url(school["school_id"], _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        json={"correct_option": _NEW_OPTION, "confirm_fork": True},
        headers=_auth(outsider),
    )
    assert r.status_code == 403, r.text
    assert (await _school_rows(client, school["school_id"]))["forks"] == []


# ── Audit ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_the_audit_row_carries_the_old_and_new_correct_text(
    client: AsyncClient, db_conn
) -> None:
    """Design §5: the audit records what changed, which for this action is the
    answer — the option LETTER alone is meaningless once options move."""
    school = await _register(client, "Corr Audit School", "corr-audit-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    with patch("src.school.answer_review_router.write_audit_log") as mock_audit:
        r = await client.post(
            _correct_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
            params={"lang": "en"},
            json={"correct_option": _NEW_OPTION, "confirm_fork": True},
            headers=_auth(token),
        )
    assert r.status_code == 200, r.text

    assert mock_audit.call_count == 1
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["event_type"] == "quiz_answer.corrected"
    metadata = kwargs["metadata"]
    assert metadata["school_id"] == school_id
    assert metadata["unit_id"] == _UNIT_ID
    assert metadata["stable_question_id"] == _stable_id()
    assert metadata["old_correct_text"] == _STORE_TEXT
    assert metadata["new_correct_text"] == _NEW_TEXT
    assert metadata["created"] == {"adoption": True, "fork": True, "import": True}


# ── #806: approving must not leave the cache lying ────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_approving_an_override_reaches_the_student_immediately(
    client: AsyncClient, db_conn
) -> None:
    """#806, fixed where it belongs: `approve_unit_content`.

    `get_active_override` caches a JSON-null MISS sentinel for an hour, and the
    approve endpoint — unlike the separate publish endpoint (school/router.py
    :3296-3305) — never cleared it. So a school's FIRST override for a unit
    could stay invisible to serving and grading for up to an hour after it was
    approved and published.

    The student sits the quiz BEFORE the override exists, which is what caches
    the sentinel. A test that approves first and reads afterwards passes while
    the bug is live — that is the whole point of it.

    Driven through the school's own approve endpoint, not through the correction
    path, so it fails if the fix is put in the correction instead.
    """
    school = await _register(client, "Corr 806 School", "corr-806-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    adoption_id = await _adopt(client, school_id, token)
    fork_id = await _import(client, school_id, token, adoption_id, _UNIT_ID)

    _student, student_token = await _student_of(client, school_id)
    before = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert before["score"] == 0, "the store still answers — and the miss is now cached"
    await _warm_the_override_cache(client, school_id)

    base = f"/api/v1/schools/{school_id}/content/{fork_id}/units/{_UNIT_ID}"
    for n in (1, 2, 3):
        edited = json.loads(json.dumps(_STORE_BODY))
        edited["questions"][0]["correct_option"] = _NEW_OPTION
        r = await client.put(
            f"{base}/overrides/quiz_set_{n}",
            json={"body": edited, "lang": "en"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text

    r2 = await client.post(f"{base}/review", json={"lang": "en"}, headers=_auth(token))
    assert r2.status_code == 200, r2.text
    r3 = await client.post(
        f"{base}/approve", json={"lang": "en", "publish": True}, headers=_auth(token)
    )
    assert r3.status_code == 200, r3.text

    after = await _sit_the_quiz(client, student_token, picked=_NEW_INDEX)
    assert after["score"] == 1, "approve+publish must be live immediately, not in an hour"
