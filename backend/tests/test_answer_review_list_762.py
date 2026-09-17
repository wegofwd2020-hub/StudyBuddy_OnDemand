"""
tests/test_answer_review_list_762.py

Task 2 (#762) — GET /schools/{school_id}/content/{curriculum_id}/units/{unit_id}/answers

Lists every quiz question of a unit with its correct answer, whether THIS
school has checked it, and how many of THIS school's own students flagged it.

Fixtures follow the adopt -> import -> save-draft -> review -> approve flow
used by test_epic12_content_authoring.py rather than hand-rolled override SQL,
so the "override" scenario this file exercises is the same one the real API
mints in production, not a shape this test invented.
"""

from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app

from src.core.storage import LocalStorage
from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"

_OOB_CURRICULUM_ID = "test-oob-g8-762"
_UNIT_ID = "test-oob-g8-762-MATH-U01"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _answers_url(school_id: str, curriculum_id: str) -> str:
    return f"/api/v1/schools/{school_id}/content/{curriculum_id}/units/{_UNIT_ID}/answers"


def _quiz_body(*, correct: str) -> dict:
    return {
        "questions": [
            {
                "question_id": "q1",
                "question_text": "What is 6 x 7?",
                "options": [
                    {"option_id": "A", "text": "42"},
                    {"option_id": "B", "text": "36"},
                ],
                "correct_option": correct,
                "explanation": "6 times 7 is 42.",
            }
        ]
    }


# The store always says A (42) is correct; the school's override (deliberately)
# says B — so a test can tell which source answered a given set.
_STORE_BODY = _quiz_body(correct="A")
_OVERRIDE_SET_1_BODY = _quiz_body(correct="B")


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def oob_curriculum(client: AsyncClient) -> dict:
    """One committed platform curriculum + unit, shared by every test in this
    module. Inserted via the app's own pool (not the rolling `db_conn`
    transaction) so the request-handling connections used by `client` can
    actually see it."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO curricula
            (curriculum_id, name, grade, year, is_default,
             owner_type, status, source_type, retention_status)
        VALUES ($1, $2, 8, 2026, TRUE, 'platform', 'active', 'default', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _OOB_CURRICULUM_ID,
        "Grade 8 Math (762 test)",
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
    """Point app.state.storage at a tmp LocalStorage carrying 3 quiz sets for
    the test unit, each with the SAME single question (store says A/42)."""
    unit_dir = tmp_path / "curricula" / _OOB_CURRICULUM_ID / _UNIT_ID
    unit_dir.mkdir(parents=True)
    for n in (1, 2, 3):
        (unit_dir / f"quiz_set_{n}_en.json").write_text(json.dumps(_STORE_BODY))

    old_storage = app.state.storage
    app.state.storage = LocalStorage(root=str(tmp_path))
    yield tmp_path
    app.state.storage = old_storage


async def _adopt_and_import(
    client: AsyncClient, school_id: str, token: str, curriculum_id: str, unit_id: str
) -> tuple[str, str]:
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": curriculum_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    adoption_id = r.json()["adoption_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{unit_id}/import",
        headers=_auth(token),
    )
    assert r2.status_code == 201, r2.text
    return adoption_id, r2.json()["forked_curriculum_id"]


async def _override_quiz_set_1(
    client: AsyncClient, school_id: str, token: str, fork_id: str, unit_id: str
) -> None:
    r = await client.put(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/overrides/quiz_set_1",
        json={"body": _OVERRIDE_SET_1_BODY, "lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "quiz_set_1"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text

    r3 = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/approve",
        json={"lang": "en", "content_type": "quiz_set_1", "publish": True},
        headers=_auth(token),
    )
    assert r3.status_code == 200, r3.text


# ── Every question, correct answer, stable id ─────────────────────────────────


@pytest.mark.asyncio
async def test_every_question_of_every_set_is_listed_with_correct_answer_and_stable_id(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "List All School", "list-all-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert len(data["questions"]) == 3  # one question x 3 sets
    seen_sets = {q["set_number"] for q in data["questions"]}
    assert seen_sets == {1, 2, 3}
    for q in data["questions"]:
        assert q["correct_option"] == "A"
        assert q["stable_question_id"]
        assert q["question_text"] == "What is 6 x 7?"
        assert {o["option_id"] for o in q["options"]} == {"A", "B"}


# ── Ownership resolution ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ownership_is_none_for_an_unadopted_platform_curriculum(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The demo's actual case (2026-09-17 design doc): a school reaches this
    curriculum via a classroom package and has never adopted it."""
    school = await _register(client, "Unadopted School", "unadopted-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ownership"] == "none"
    assert data["serving_curriculum_id"] == _OOB_CURRICULUM_ID


@pytest.mark.asyncio
async def test_ownership_is_fork_when_owned_but_no_override_exists_yet(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Fork Only School", "fork-only-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)

    r = await client.get(
        _answers_url(school_id, fork_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ownership"] == "fork"
    assert all(q["correct_option"] == "A" for q in data["questions"])  # all still from the store


@pytest.mark.asyncio
async def test_ownership_is_override_and_the_listed_body_is_the_overrides_not_the_stores(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Override School", "override-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)
    await _override_quiz_set_1(client, school_id, token, fork_id, _UNIT_ID)

    r = await client.get(
        _answers_url(school_id, fork_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ownership"] == "override"

    by_set = {q["set_number"]: q for q in data["questions"]}
    assert by_set[1]["correct_option"] == "B"  # the OVERRIDE's answer, not the store's "A"
    assert by_set[2]["correct_option"] == "A"  # untouched set still reads the store
    assert by_set[3]["correct_option"] == "A"


# ── Validation state ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validated_is_null_before_any_validation(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "No Validation Yet School", "no-val-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    assert all(q["validated"] is None for q in r.json()["questions"])


# ── Flag counts, scoped per school ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flag_count_covers_only_this_schools_own_students(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    pool = client._transport.app.state.pool

    school_a = await _register(client, "Flag School A", "flag-a-762@example.com")
    school_b = await _register(client, "Flag School B", "flag-b-762@example.com")

    # Discover the real stable id the listing computes, rather than
    # recomputing the hash independently in the test.
    r0 = await client.get(
        _answers_url(school_a["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school_a["access_token"]),
    )
    stable_id = next(q for q in r0.json()["questions"] if q["set_number"] == 1)[
        "stable_question_id"
    ]

    for school, n_flags in ((school_a, 2), (school_b, 1)):
        student_id = uuid.uuid4()
        email = f"{student_id}@example.com"
        await pool.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, name, email, grade, locale, account_status)
            VALUES ($1, $2, 'Flag Student', $3, 8, 'en', 'active')
            ON CONFLICT (student_id) DO NOTHING
            """,
            student_id,
            f"local:{student_id}",
            email,
        )
        await pool.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (school_id, student_email) DO NOTHING
            """,
            school["school_id"],
            email,
            student_id,
        )
        for _ in range(n_flags):
            await pool.execute(
                """
                INSERT INTO feedback
                    (student_id, category, unit_id, curriculum_id, content_type,
                     helpful, stable_question_id)
                VALUES ($1, 'content', $2, $3, 'quiz', FALSE, $4)
                """,
                student_id,
                _UNIT_ID,
                _OOB_CURRICULUM_ID,
                stable_id,
            )

    r_a = await client.get(
        _answers_url(school_a["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school_a["access_token"]),
    )
    q1_a = next(q for q in r_a.json()["questions"] if q["set_number"] == 1)
    assert q1_a["flag_count"] == 2  # only school A's own two flags, not B's

    r_b = await client.get(
        _answers_url(school_b["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school_b["access_token"]),
    )
    q1_b = next(q for q in r_b.json()["questions"] if q["set_number"] == 1)
    assert q1_b["flag_count"] == 1  # only school B's own one flag, not A's


# ── Permissions ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_from_another_school_is_forbidden(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Owner School", "owner-762@example.com")
    other_school_token = make_teacher_token(school_id=str(uuid.uuid4()), role="teacher")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(other_school_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_teacher_without_curriculum_capability_is_forbidden(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Plain Teacher School", "plain-762@example.com")
    plain_teacher_token = make_teacher_token(school_id=school["school_id"], role="teacher")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(plain_teacher_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_succeeds(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Admin Success School", "admin-succ-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),  # the founder token's role is school_admin
    )
    assert r.status_code == 200, r.text
