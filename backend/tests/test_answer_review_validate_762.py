"""
tests/test_answer_review_validate_762.py

Task 3 (#762) — POST .../answers/{stable_question_id}/validate

Records that THIS school's reviewer has checked a question's correct answer,
snapshotting the correct option's text so the tick can later be shown as
"needs re-checking" rather than vouching for an answer nobody checked.

Fixtures are imported from test_answer_review_list_762 rather than re-declared:
the two endpoints resolve a question through the SAME path, and a second,
subtly different fixture would let them drift apart without a test noticing.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.core.question_identity import stable_question_id
from tests.helpers.token_factory import make_teacher_token
from tests.test_answer_review_list_762 import (
    _OOB_CURRICULUM_ID,
    _UNIT_ID,
    _adopt_and_import,
    _answers_url,
    _auth,
    _override_quiz_set_1,
    _register,
    oob_curriculum,  # noqa: F401 — imported to REGISTER the fixture; requested via usefixtures
    quiz_content_store,  # noqa: F401 — same: importing it is what makes it resolvable here
)

# The one question the shared fixture puts in all three sets. The store says
# A ("42"); the school's override (when a test creates one) says B ("36").
_STEM = "What is 6 x 7?"
_STORE_CORRECT_TEXT = "42"
_OVERRIDE_CORRECT_TEXT = "36"


def _stable_id(stem: str = _STEM) -> str:
    """The id the GRADER mints — source curriculum, unit, the language the file
    was actually read in. `test_answer_review_list_762` pins the listing to this
    same value against `resolve_quiz_answer_key`, so computing it here keeps the
    validate tests off the endpoint's own output (a circular assertion would
    pass even if both sides agreed on an id nothing else recognises)."""
    return stable_question_id(_OOB_CURRICULUM_ID, _UNIT_ID, "en", stem)


def _validate_url(school_id: str, curriculum_id: str, stable_id: str) -> str:
    return (
        f"/api/v1/schools/{school_id}/content/{curriculum_id}"
        f"/units/{_UNIT_ID}/answers/{stable_id}/validate"
    )


async def _rows(client: AsyncClient, school_id: str) -> list[dict]:
    pool = client._transport.app.state.pool
    rows = await pool.fetch(
        """
        SELECT stable_question_id, correct_text, validated_by::text AS validated_by,
               validated_at
        FROM question_validations WHERE school_id = $1::uuid
        """,
        school_id,
    )
    return [dict(r) for r in rows]


async def _provision_reviewer(
    client: AsyncClient, school_id: str, admin_token: str, email: str
) -> str:
    """A real `teachers` row holding `curriculum.review`.

    Real because `question_validations.validated_by` is a FK to `teachers` — a
    token minted over an id that was never provisioned would fail on the insert,
    not on the guard, and the permission assertion would be meaningless.
    """
    from unittest.mock import AsyncMock

    with patch("src.email.service.send_welcome_teacher_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Reviewer", "email": email},
            headers=_auth(admin_token),
        )
    assert r.status_code == 201, r.text
    teacher_id = r.json()["teacher_id"]

    r2 = await client.put(
        f"/api/v1/schools/{school_id}/teachers/{teacher_id}/capabilities",
        json={"capabilities": ["curriculum.review"]},
        headers=_auth(admin_token),
    )
    assert r2.status_code == 200, r2.text
    return teacher_id


# ── The row it writes, and the tick the listing then reads back ───────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_validating_stores_the_current_correct_text_and_reads_back_checked(
    client: AsyncClient, db_conn
) -> None:
    school = await _register(client, "Validate School", "validate-762@example.com")
    school_id, token = school["school_id"], school["access_token"]
    stable_id = _stable_id()

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, stable_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["validated_by"] == school["teacher_id"]
    assert body["validated_at"]

    rows = await _rows(client, school_id)
    assert len(rows) == 1
    assert rows[0]["stable_question_id"] == stable_id
    # The TEXT, not the option letter: "correct_option: A" is meaningless once
    # the options have been reordered, which is exactly the edit that must not
    # silently invalidate a tick.
    assert rows[0]["correct_text"] == _STORE_CORRECT_TEXT

    r2 = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    questions = r2.json()["questions"]
    assert len(questions) == 3
    for q in questions:
        assert q["validated"] is not None, q["set_number"]
        assert q["validated"]["by"] == school["teacher_id"]
        assert q["validated"]["stale"] is False, q["set_number"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_the_tick_goes_stale_once_the_correct_answer_changes(
    client: AsyncClient, db_conn
) -> None:
    """Storing the TEXT is the point of the column.

    A reviewer checks the question while the platform's "42" is correct; the
    school then overrides set 1 to say "36". Set 1's tick must read
    "needs re-checking"; sets 2 and 3 still say 42, so they stay ticked. One
    row, two verdicts — the comparison is against each SET's current answer.

    Validation happens BEFORE the adoption on purpose: with ownership "none"
    the listing never calls `get_active_override`, so no JSON-null miss
    sentinel is cached for the sets, and the later GET reads the real override
    instead of an hour-old cached absence.
    """
    school = await _register(client, "Stale Validate School", "stale-validate-762@example.com")
    school_id, token = school["school_id"], school["access_token"]
    stable_id = _stable_id()

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, stable_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert (await _rows(client, school_id))[0]["correct_text"] == _STORE_CORRECT_TEXT

    _, fork_id = await _adopt_and_import(client, school_id, token, _OOB_CURRICULUM_ID, _UNIT_ID)
    await _override_quiz_set_1(client, school_id, token, fork_id, _UNIT_ID)

    r2 = await client.get(
        _answers_url(school_id, fork_id),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    by_set = {q["set_number"]: q for q in r2.json()["questions"]}
    assert by_set[1]["correct_option"] == "B", "the override answers set 1"
    assert by_set[1]["validated"]["stale"] is True
    assert by_set[2]["validated"]["stale"] is False
    assert by_set[3]["validated"]["stale"] is False


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_second_school_validating_leaves_the_first_schools_row_alone(
    client: AsyncClient, db_conn
) -> None:
    """The PK is (school_id, stable_question_id). An upsert keyed on the
    question alone would let the second school overwrite the first's reviewer
    and timestamp — the same question, checked by two schools, is two
    independent facts (design decision 1: scope is the school's own copy)."""
    school_a = await _register(client, "Val School A", "val-a-762@example.com")
    school_b = await _register(client, "Val School B", "val-b-762@example.com")
    stable_id = _stable_id()

    for school in (school_a, school_b):
        r = await client.post(
            _validate_url(school["school_id"], _OOB_CURRICULUM_ID, stable_id),
            params={"lang": "en"},
            headers=_auth(school["access_token"]),
        )
        assert r.status_code == 200, r.text

    for school in (school_a, school_b):
        rows = await _rows(client, school["school_id"])
        assert len(rows) == 1
        assert rows[0]["stable_question_id"] == stable_id
        assert rows[0]["validated_by"] == school["teacher_id"]


# ── Who may write ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_plain_teacher_is_refused(client: AsyncClient, db_conn) -> None:
    """Any teacher may LOOK (require_curriculum_view on the GET); validating is
    `require_review`."""
    school = await _register(client, "Plain Val School", "plain-val-762@example.com")
    school_id = school["school_id"]
    plain = make_teacher_token(school_id=school_id, role="teacher")

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        headers=_auth(plain),
    )
    assert r.status_code == 403
    assert await _rows(client, school_id) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_commission_only_teacher_is_refused(client: AsyncClient, db_conn) -> None:
    """The case that tells the two guards apart.

    A teacher with NO capability is refused by `require_curriculum_view` and by
    `require_review` alike, so the plain-teacher test above would pass even if
    this endpoint were gated at the GET's looser tier. `curriculum.commission`
    clears the view gate and not the review gate, so this is the only assertion
    that pins which guard is actually in front of the write.
    """
    school = await _register(client, "Commission Val School", "comm-val-762@example.com")
    school_id = school["school_id"]
    token = make_teacher_token(
        school_id=school_id, role="teacher", capabilities=["curriculum.commission"]
    )

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 403
    assert await _rows(client, school_id) == []

    # …and the same token CAN look, which is what makes the refusal above a
    # statement about the tier rather than about the token.
    r2 = await client.get(
        _answers_url(school_id, _OOB_CURRICULUM_ID),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_curriculum_review_teacher_succeeds(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Reviewer Val School", "rev-val-762@example.com")
    school_id, admin = school["school_id"], school["access_token"]
    teacher_id = await _provision_reviewer(client, school_id, admin, "rev-t-762@example.com")
    token = make_teacher_token(
        teacher_id=teacher_id,
        school_id=school_id,
        role="teacher",
        capabilities=["curriculum.review"],
    )

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["validated_by"] == teacher_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_token_naming_a_teacher_who_no_longer_exists_is_refused_not_a_500(
    client: AsyncClient, db_conn
) -> None:
    """`validated_by` is a FK to `teachers`, and a JWT outlives the row it names.

    `scripts/purge_account.py` hard-deletes a teacher by email, so a token
    minted minutes earlier clears the guard and then violates the FK on the
    insert. Unhandled, that is a 500 with a Postgres constraint name in the
    logs; a reviewer gets a blank failure and no reason to sign in again.
    """
    school = await _register(client, "Ghost Val School", "ghost-val-762@example.com")
    school_id = school["school_id"]
    ghost = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-00000000762a",
        school_id=school_id,
        role="teacher",
        capabilities=["curriculum.review"],  # clears the guard; the row is gone
    )

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        headers=_auth(ghost),
    )
    assert r.status_code == 403, r.text
    assert await _rows(client, school_id) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_a_school_admin_succeeds(client: AsyncClient, db_conn) -> None:
    """`school_admin` is an implicit superset (permissions.py) — not a
    special case in this endpoint."""
    school = await _register(client, "Admin Val School", "admin-val-762@example.com")

    r = await client.post(
        _validate_url(school["school_id"], _OOB_CURRICULUM_ID, _stable_id()),
        params={"lang": "en"},
        headers=_auth(school["access_token"]),  # the founder token is school_admin
    )
    assert r.status_code == 200, r.text


# ── An id that is not in this unit ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_an_unknown_question_id_is_404_and_writes_nothing(
    client: AsyncClient, db_conn
) -> None:
    """`stable_question_id` is a hash the caller supplies, and the table has no
    FK that could reject it. Without resolving it through the listing first,
    any 16 characters would mint a validation row for a question that does not
    exist in this unit — a tick against nothing, which the listing could never
    show and no one could ever clear.

    Carries its own positive control: a route that does not exist answers 404
    to everything, so "an unknown id 404s" is true of an unimplemented
    endpoint. The known id must succeed in the same test, and the 404 must be
    THIS endpoint's structured refusal rather than FastAPI's bare
    `{"detail": "Not Found"}`.
    """
    school = await _register(client, "Unknown Q School", "unknown-q-762@example.com")
    school_id, token = school["school_id"], school["access_token"]
    known = _stable_id()
    absent = _stable_id("A question that is in no set of this unit")

    ok = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, known),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert ok.status_code == 200, ok.text

    r = await client.post(
        _validate_url(school_id, _OOB_CURRICULUM_ID, absent),
        params={"lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 404, r.text
    # A route that does not exist answers Starlette's bare {"detail": "Not
    # Found"}; the app's handler stamps `error` on every refusal it raises.
    assert r.json()["error"] == "not_found", "the endpoint's refusal, not the router's"

    rows = await _rows(client, school_id)
    assert [row["stable_question_id"] for row in rows] == [known]


# ── Audit ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("oob_curriculum", "quiz_content_store")
async def test_an_audit_row_is_written(client: AsyncClient, db_conn) -> None:
    school = await _register(client, "Audit Val School", "audit-val-762@example.com")
    school_id, token = school["school_id"], school["access_token"]
    stable_id = _stable_id()

    with patch("src.school.answer_review_router.write_audit_log") as mock_audit:
        r = await client.post(
            _validate_url(school_id, _OOB_CURRICULUM_ID, stable_id),
            params={"lang": "en"},
            headers=_auth(token),
        )
    assert r.status_code == 200, r.text

    assert mock_audit.call_count == 1
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["event_type"] == "quiz_answer.validated"
    metadata = kwargs["metadata"]
    assert metadata["school_id"] == school_id
    assert metadata["unit_id"] == _UNIT_ID
    assert metadata["stable_question_id"] == stable_id
