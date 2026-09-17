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

from src.core.question_identity import stable_question_id
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


async def _grader_key(
    client: AsyncClient, *, school_id: str, set_number: int, lang: str = "en"
) -> dict:
    """The answer key the REAL grading path resolves for this school.

    Deliberately called with the SOURCE curriculum id: that is what
    `progress_sessions.curriculum_id` holds (the fork→OOB swap is applied when
    the session is created), so it is the input every recorded
    `stable_question_id` was minted from. Comparing the listing against THIS is
    the whole point — an id that matches nothing joins to nothing, and the flag
    count is silently 0 forever.
    """
    from src.content.service import resolve_quiz_answer_key

    state = client._transport.app.state
    return await resolve_quiz_answer_key(
        school_id,
        _OOB_CURRICULUM_ID,
        _UNIT_ID,
        set_number,
        lang,
        state.pool,
        state.redis,
        state.storage,
    )


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
    by_set = {q["set_number"]: q for q in data["questions"]}
    assert set(by_set) == {1, 2, 3}
    for q in data["questions"]:
        assert q["correct_option"] == "A"
        assert q["correct_option_resolves"] is True
        assert q["served_from"] == "store"
        assert q["question_text"] == "What is 6 x 7?"
        assert {o["option_id"] for o in q["options"]} == {"A", "B"}

    # The identity must be the GRADER's, not merely non-empty. A truthy
    # assertion passes on any hash at all, including one that matches nothing
    # ever recorded — which is exactly the failure mode this endpoint has to
    # avoid, since every join it does is on this id.
    for set_number in (1, 2, 3):
        key = await _grader_key(client, school_id=school["school_id"], set_number=set_number)
        assert by_set[set_number]["stable_question_id"] == key["q1"]["stable_question_id"], (
            set_number
        )


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
    assert data["source_curriculum_id"] == _OOB_CURRICULUM_ID
    assert data["owned_curriculum_id"] is None


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
    assert data["source_curriculum_id"] == _OOB_CURRICULUM_ID
    assert data["owned_curriculum_id"] == fork_id
    assert all(q["correct_option"] == "A" for q in data["questions"])  # all still from the store
    assert all(q["served_from"] == "store" for q in data["questions"])


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
    assert data["source_curriculum_id"] == _OOB_CURRICULUM_ID
    assert data["owned_curriculum_id"] == fork_id

    by_set = {q["set_number"]: q for q in data["questions"]}
    assert by_set[1]["correct_option"] == "B"  # the OVERRIDE's answer, not the store's "A"
    assert by_set[2]["correct_option"] == "A"  # the imported copy, unedited
    assert by_set[3]["correct_option"] == "A"
    # All three read from an override here: an import bundles every content type
    # it finds, and approving one member approves and publishes the bundle. Sets
    # 2 and 3 are therefore the school's own copies of the platform's body — the
    # same words, a different row, which is why `served_from` is per question
    # rather than a property of the response.
    assert all(q["served_from"] == "override" for q in data["questions"])

    # The identity of an overridden question is still the GRADER's. The override
    # is keyed by the fork, but nothing was ever RECORDED under the fork id:
    # `progress_answers` and `feedback` both carry H(source, unit, lang, stem),
    # because the session stores the swapped id.
    for set_number in (1, 2, 3):
        key = await _grader_key(client, school_id=school_id, set_number=set_number)
        assert by_set[set_number]["stable_question_id"] == key["q1"]["stable_question_id"], (
            set_number
        )


@pytest.mark.asyncio
async def test_one_response_can_mix_the_override_and_the_store(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """`served_from` is per question because a unit can be half and half.

    The active pointers for sets 2 and 3 are dropped here — the state a school
    reaches by reverting them, or by importing a unit whose other sets were not
    on disk at the time. Resolution then has to fall back per SET, exactly as
    serving does, rather than deciding once for the unit.
    """
    school = await _register(client, "Mixed School", "mixed-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)
    await _override_quiz_set_1(client, school_id, token, fork_id, _UNIT_ID)

    pool = client._transport.app.state.pool
    await pool.execute(
        """
        DELETE FROM unit_content_active_versions
        WHERE school_id = $1::uuid AND curriculum_id = $2 AND unit_id = $3
          AND content_type = ANY(ARRAY['quiz_set_2', 'quiz_set_3'])
        """,
        school_id,
        fork_id,
        _UNIT_ID,
    )

    r = await client.get(
        _answers_url(school_id, fork_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ownership"] == "override"

    by_set = {q["set_number"]: q for q in data["questions"]}
    assert by_set[1]["served_from"] == "override"
    assert by_set[2]["served_from"] == "store"
    assert by_set[3]["served_from"] == "store"
    assert by_set[2]["correct_option"] == "A"


@pytest.mark.asyncio
async def test_a_school_that_owns_a_fork_is_told_so_through_the_platform_id(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The Unit Performance report — the spec's primary and, on the demo, only
    workable entry point — carries the PLATFORM curriculum id, because that is
    what the classroom package holds. Answering `ownership: "none"` there would
    offer a school a fork-confirmation for a copy it already has, and would list
    the platform's questions rather than the ones its own students sit.
    """
    school = await _register(client, "Reverse Lookup School", "reverse-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)
    await _override_quiz_set_1(client, school_id, token, fork_id, _UNIT_ID)

    r = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),  # the PLATFORM id, not the fork
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["ownership"] == "override"
    assert data["owned_curriculum_id"] == fork_id
    assert data["source_curriculum_id"] == _OOB_CURRICULUM_ID

    by_set = {q["set_number"]: q for q in data["questions"]}
    assert by_set[1]["correct_option"] == "B"  # what this school's students sit
    assert by_set[1]["served_from"] == "override"


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


async def _validate(
    client: AsyncClient, school: dict, *, stable_id: str, correct_text: str
) -> None:
    """Record that this school checked `stable_id`, snapshotting `correct_text`."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO question_validations
            (school_id, stable_question_id, correct_text, validated_by)
        VALUES ($1::uuid, $2, $3, $4::uuid)
        """,
        school["school_id"],
        stable_id,
        correct_text,
        school["teacher_id"],
    )


@pytest.mark.asyncio
async def test_a_checked_answer_reads_back_as_checked(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school = await _register(client, "Checked School", "checked-762@example.com")

    key = await _grader_key(client, school_id=school["school_id"], set_number=1)
    await _validate(client, school, stable_id=key["q1"]["stable_question_id"], correct_text="42")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    by_set = {q["set_number"]: q for q in r.json()["questions"]}

    assert by_set[1]["validated"] is not None
    assert by_set[1]["validated"]["by"] == school["teacher_id"]
    assert by_set[1]["validated"]["stale"] is False, "the correct answer is still 42"


@pytest.mark.asyncio
async def test_a_tick_goes_stale_when_the_correct_answer_changes(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """The snapshot is the whole point of `correct_text`.

    A reviewer checked this question while the platform's "42" was correct; the
    school then corrected set 1 to "36". The tick must read "needs re-checking"
    rather than vouching for an answer nobody checked.

    Sets 2 and 3 share the question's stem, so they share its identity and that
    one validation row — and they still say 42, so they stay ticked. One row,
    two verdicts: the comparison is per SET's current answer, not per row.
    """
    school = await _register(client, "Stale School", "stale-762@example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)
    await _override_quiz_set_1(client, school_id, token, fork_id, _UNIT_ID)

    # Computed rather than read back from the endpoint, and NOT via the grader:
    # resolving a key before the override is published caches the miss sentinel
    # for an hour (`get_active_override`), and the approve endpoint does not
    # clear it — which would make this test pass or fail on a cache, not on the
    # comparison it is about.
    stable_id = stable_question_id(_OOB_CURRICULUM_ID, _UNIT_ID, "en", "What is 6 x 7?")
    await _validate(client, school, stable_id=stable_id, correct_text="42")

    r = await client.get(
        _answers_url(school_id, fork_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    by_set = {q["set_number"]: q for q in r.json()["questions"]}

    assert by_set[1]["correct_option"] == "B"
    assert by_set[1]["validated"]["stale"] is True
    assert by_set[2]["validated"]["stale"] is False


# ── Flag counts, scoped per school ──────────────────────────────────────────────


async def _enrol_student(client: AsyncClient, school_id: str, *, email: str | None = None) -> str:
    """A student on this school's roster. Returns the student_id."""
    pool = client._transport.app.state.pool
    student_id = uuid.uuid4()
    address = email or f"{student_id}@example.com"
    await pool.execute(
        """
        INSERT INTO students
            (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Flag Student', $3, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        student_id,
        f"local:{student_id}",
        address,
    )
    await _enrol(client, school_id, str(student_id), address)
    return str(student_id)


async def _enrol(client: AsyncClient, school_id: str, student_id: str, email: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO school_enrolments (school_id, student_email, student_id, status)
        VALUES ($1, $2, $3::uuid, 'active')
        ON CONFLICT (school_id, student_email) DO NOTHING
        """,
        school_id,
        email,
        student_id,
    )


async def _flag(client: AsyncClient, student_id: str, stable_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO feedback
            (student_id, category, unit_id, curriculum_id, content_type,
             helpful, stable_question_id)
        VALUES ($1::uuid, 'content', $2, $3, 'quiz', FALSE, $4)
        """,
        student_id,
        _UNIT_ID,
        _OOB_CURRICULUM_ID,
        stable_id,
    )


@pytest.mark.asyncio
async def test_flag_count_covers_only_this_schools_own_students(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    school_a = await _register(client, "Flag School A", "flag-a-762@example.com")
    school_b = await _register(client, "Flag School B", "flag-b-762@example.com")

    # Seeded from the GRADER's id, not from the id this endpoint returned.
    # Seeding from the response makes the test circular: the count would come
    # out right even if the endpoint identified questions in a way that matches
    # nothing a student's flag was ever recorded under.
    key = await _grader_key(client, school_id=school_a["school_id"], set_number=1)
    stable_id = key["q1"]["stable_question_id"]

    for school, n_flags in ((school_a, 2), (school_b, 1)):
        student_id = await _enrol_student(client, school["school_id"])
        for _ in range(n_flags):
            await _flag(client, student_id, stable_id)

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


@pytest.mark.asyncio
async def test_a_second_enrolment_row_does_not_double_the_count(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """`school_enrolments` is UNIQUE (school_id, student_email) — NOT on
    (school_id, student_id). One person under two addresses at one school is two
    rows, so JOINing the roster onto `feedback` counts every flag once per row.

    Repo rule from #623/#625: aggregate the child table, then join. A count that
    inflates with the number of times someone was added is worse than no count —
    the page sorts by it.
    """
    school = await _register(client, "Two Rows School", "two-rows-762@example.com")

    key = await _grader_key(client, school_id=school["school_id"], set_number=1)
    stable_id = key["q1"]["stable_question_id"]

    student_id = await _enrol_student(client, school["school_id"])
    await _enrol(client, school["school_id"], student_id, "second-address-762@example.com")
    await _flag(client, student_id, stable_id)
    await _flag(client, student_id, stable_id)

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    q1 = next(q for q in r.json()["questions"] if q["set_number"] == 1)
    assert q1["flag_count"] == 2, "two flags, counted once each"


@pytest.mark.asyncio
async def test_a_pending_enrolment_does_not_contribute_flags(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """`status = 'active'` — every sibling query in `src/reports/service.py`
    scopes this way, and an invited-but-never-joined address is not a student of
    the school for reporting purposes."""
    pool = client._transport.app.state.pool
    school = await _register(client, "Pending School", "pending-762@example.com")

    key = await _grader_key(client, school_id=school["school_id"], set_number=1)
    stable_id = key["q1"]["stable_question_id"]

    student_id = uuid.uuid4()
    email = f"{student_id}@example.com"
    await pool.execute(
        """
        INSERT INTO students
            (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Pending Student', $3, 8, 'en', 'active')
        """,
        student_id,
        f"local:{student_id}",
        email,
    )
    await pool.execute(
        """
        INSERT INTO school_enrolments (school_id, student_email, student_id, status)
        VALUES ($1, $2, $3, 'pending')
        """,
        school["school_id"],
        email,
        student_id,
    )
    await _flag(client, str(student_id), stable_id)

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),
    )
    q1 = next(q for q in r.json()["questions"] if q["set_number"] == 1)
    assert q1["flag_count"] == 0


# ── Language ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_missing_translation_is_identified_by_the_language_it_was_read_in(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """Only `_en` files exist, so `?lang=fr` reads English — and the identity has
    to say English.

    `get_quiz_answer_key` carries the rule in a comment: hashing with the
    REQUESTED language "would mint a French id for English questions and split
    one item's statistics across two identities". The file SELECTION here is
    right (serving falls back the same way); only the hash was wrong.
    """
    school = await _register(client, "French School", "french-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "fr"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 200, r.text
    questions = r.json()["questions"]
    assert len(questions) == 3, "the English files answer a French request"

    key = await _grader_key(client, school_id=school["school_id"], set_number=1, lang="fr")
    q1 = next(q for q in questions if q["set_number"] == 1)
    assert q1["stable_question_id"] == key["q1"]["stable_question_id"]
    assert q1["stable_question_id"] == stable_question_id(
        _OOB_CURRICULUM_ID, _UNIT_ID, "en", "What is 6 x 7?"
    )


@pytest.mark.asyncio
async def test_a_malformed_lang_is_refused_before_it_reaches_a_filename(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store
) -> None:
    """`lang` is interpolated into a path and `LocalStorage._full` has no
    traversal guard."""
    school = await _register(client, "Traversal School", "traversal-762@example.com")

    r = await client.get(
        _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
        params={"lang": "../../etc"},
        headers=_auth(school["access_token"]),
    )
    assert r.status_code == 422


# ── Defective content is what a reviewer opens this page to find ──────────────


@pytest.mark.asyncio
async def test_a_defective_question_is_flagged_and_a_broken_one_is_skipped(
    client: AsyncClient, db_conn, oob_curriculum, quiz_content_store, caplog
) -> None:
    """`correct_option: "C"` beside options A, B and D is a real defect —
    `_parse_quiz_answer_key` logs `quiz_answer_key_unresolvable` and grades
    nobody on it. Rendering it silently beside the options is the one thing this
    page must not do.

    A question that is structurally broken is skipped rather than 500ing the
    whole listing: one bad row must not hide the other twenty.
    """
    unit_dir = quiz_content_store / "curricula" / _OOB_CURRICULUM_ID / _UNIT_ID
    (unit_dir / "quiz_set_3_en.json").write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "question_id": "q1",
                        "question_text": "Which is defective?",
                        "options": [
                            {"option_id": "A", "text": "42"},
                            {"option_id": "B", "text": "36"},
                        ],
                        "correct_option": "C",  # names no option that exists
                    },
                    {"question_text": "No id at all"},  # structurally broken
                    "not even a question",  # not a mapping
                ]
            }
        )
    )

    school = await _register(client, "Defective School", "defective-762@example.com")

    with caplog.at_level("WARNING"):
        r = await client.get(
            _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
            params={"lang": "en"},
            headers=_auth(school["access_token"]),
        )
    assert r.status_code == 200, r.text

    by_set = {q["set_number"]: q for q in r.json()["questions"]}
    assert len(r.json()["questions"]) == 3, "one question survives in set 3, not two"
    assert by_set[3]["correct_option_resolves"] is False
    assert by_set[1]["correct_option_resolves"] is True
    assert "answer_review_question_skipped" in caplog.text


@pytest.mark.asyncio
async def test_a_unit_with_no_quiz_says_which_sets_were_missing(
    client: AsyncClient, db_conn, oob_curriculum, caplog
) -> None:
    """ "No quiz", "placeholder content refused" and "the store threw" all return
    `200 {"questions": []}`. The reviewer cannot tell them apart, so the log has
    to."""
    school = await _register(client, "Empty School", "empty-762@example.com")

    with caplog.at_level("INFO"):
        r = await client.get(
            _answers_url(school["school_id"], _OOB_CURRICULUM_ID),
            params={"lang": "en"},
            headers=_auth(school["access_token"]),
        )
    assert r.status_code == 200, r.text
    assert r.json()["questions"] == []
    assert "answer_review_sets_missing" in caplog.text


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
