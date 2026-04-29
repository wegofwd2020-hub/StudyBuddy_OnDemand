"""
tests/test_epic12_content_authoring.py

Epic 12 — Teacher Content Authoring tests (TA-0 through TA-4).

Coverage (matches spec test cases TA-TC-00 through TA-TC-26):
  TA-0  School curriculum library
    TC-00a  Empty library on new school → empty adoptions list
    TC-00b  school_admin adopts OOB curriculum → adoption row created
    TC-00b  Adopt is idempotent → 201 returned with existing row
    TC-00b  Non-platform curriculum → 422
    TC-00b  plain teacher cannot adopt → 403
    TC-00c  Deactivate adoption → status becomes 'deactivated'
    TC-00e  Two schools adopt the same OOB curriculum → independent rows, no collision

  TA-2  Import
    TC-01   First import creates fork + grade_curriculum_assignment + override rows
    TC-02   Second unit import reuses existing fork (fork_created=False)
    TC-21   Re-import same unit → existing rows returned with skipped=True
    TC-20   Import from curriculum not in library → 404
    TC-20   Import from deactivated adoption → 403

  TA-3  Edit + governance lifecycle
    TC-06   Save draft updates body in place (same version_number)
    TC-09   Submit for review → review_status = 'pending_review'
    TC-10   Approve + publish → active version set; unit_content_active_versions upserted
    TC-11   Approve only (publish=False) → approved, NOT yet in active versions
    TC-12   Reject with reason → review_status = 'rejected'
    TC-13   Save after rejection → new version (version_number = MAX + 1)
            Second submission after rejection creates a fresh pending_review row

  TA-4  Pipeline guard
    check_school_overrides returns school_ids when overrides exist
    check_school_overrides returns [] when no overrides for this unit

  Security
    Teacher from different school cannot call school-scoped endpoints → 403
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app

from src.core.storage import LocalStorage
from tests.helpers.token_factory import make_teacher_token

# Make the pipeline package importable (/pipeline is bind-mounted at repo root level)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── Test DB URL (mirrors conftest) ────────────────────────────────────────────

_dev_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
_TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    _dev_db_url.replace("/studybuddy", "/studybuddy_test").replace("@pgbouncer:", "@db:"),
)

# ── Fixed test IDs (Rule 9 — deterministic IDs in fixtures) ──────────────────

_OOB_CURRICULUM_ID = "test-oob-g8-epic12"
_OOB_CURRICULUM_ID_G9 = "test-oob-g9-epic12"
_OOB_UNIT_MATH = "test-oob-g8-epic12-MATH-U01"
_OOB_UNIT_SCI = "test-oob-g8-epic12-SCI-U01"

# ── Shared helpers ────────────────────────────────────────────────────────────

_PW = "SecureTestPwd1!"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Session-scoped: seed OOB platform curricula (committed; cleaned by downgrade)

@pytest_asyncio.fixture(scope="session")
async def oob_curricula():
    """
    Insert test OOB platform curricula directly into the test DB via a
    committed connection (no rolling transaction so data is visible to the
    app's connection pool across all tests in this session).

    The rows are automatically removed when run_migrations downgrades at
    session teardown — no explicit cleanup is needed here.
    """
    conn = await asyncpg.connect(_TEST_DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    # Grade 8 OOB curriculum (primary test curriculum)
    await conn.execute(
        """
        INSERT INTO curricula
            (curriculum_id, name, grade, year, is_default,
             owner_type, status, source_type, retention_status)
        VALUES ($1, $2, 8, 2026, TRUE, 'platform', 'active', 'default', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _OOB_CURRICULUM_ID,
        "Grade 8 STEM (Epic 12 test)",
    )

    # Grade 9 OOB curriculum (second school adoption test)
    await conn.execute(
        """
        INSERT INTO curricula
            (curriculum_id, name, grade, year, is_default,
             owner_type, status, source_type, retention_status)
        VALUES ($1, $2, 9, 2026, TRUE, 'platform', 'active', 'default', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _OOB_CURRICULUM_ID_G9,
        "Grade 9 STEM (Epic 12 test)",
    )

    # Curriculum units for the grade 8 OOB curriculum
    for unit_id, subject, title in [
        (_OOB_UNIT_MATH, "MATH", "Introduction to Algebra"),
        (_OOB_UNIT_SCI, "SCI", "Cell Biology"),
    ]:
        await conn.execute(
            """
            INSERT INTO curriculum_units
                (unit_id, curriculum_id, subject, title, unit_name, has_lab, sort_order)
            VALUES ($1, $2, $3, $4, $4, FALSE, 0)
            ON CONFLICT DO NOTHING
            """,
            unit_id,
            _OOB_CURRICULUM_ID,
            subject,
            title,
        )

    await conn.close()
    yield {
        "curriculum_id": _OOB_CURRICULUM_ID,
        "curriculum_id_g9": _OOB_CURRICULUM_ID_G9,
        "unit_math": _OOB_UNIT_MATH,
        "unit_sci": _OOB_UNIT_SCI,
    }


# ── Content store fixture: writes lesson_en.json for the test unit ────────────

@pytest.fixture()
def content_store_with_lesson(tmp_path):
    """
    Point app.state.storage at a tmp LocalStorage that has a lesson_en.json
    for the grade-8 math unit. Returns the tmp_path root.
    """
    lesson_body = {
        "unit_id": _OOB_UNIT_MATH,
        "subject": "Mathematics",
        "topic": "Introduction to Algebra",
        "synopsis": "Learn the basics of algebra.",
        "sections": [{"heading": "Introduction", "body": "Variables represent unknown values."}],
        "key_points": ["Variables stand for numbers."],
        "learning_objectives": ["Define a variable."],
        "reading_level": "Grade 8",
        "estimated_duration_minutes": 30,
        "language": "en",
        "generated_at": "2026-04-01T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    unit_dir = tmp_path / "curricula" / _OOB_CURRICULUM_ID / _OOB_UNIT_MATH
    unit_dir.mkdir(parents=True)
    (unit_dir / "lesson_en.json").write_text(json.dumps(lesson_body))

    old_storage = app.state.storage
    app.state.storage = LocalStorage(root=str(tmp_path))
    yield tmp_path
    app.state.storage = old_storage


# ── TA-0: School curriculum library ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_tc00a_empty_library_on_new_school(client: AsyncClient, db_conn, oob_curricula) -> None:
    """TC-00a: New school has empty library."""
    school = await _register(client, "Empty Library School", "empty-lib@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.get(f"/api/v1/schools/{school_id}/library", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["adoptions"] == []


@pytest.mark.asyncio
async def test_tc00b_adopt_oob_curriculum(client: AsyncClient, db_conn, oob_curricula) -> None:
    """TC-00b: school_admin adopts a platform OOB curriculum."""
    school = await _register(client, "Adopt School", "adopt@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["curriculum_id"] == oob_curricula["curriculum_id"]
    assert data["forked_curriculum_id"] is None  # fork created lazily on first import
    assert data["status"] == "active"
    assert data["has_overrides"] is False


@pytest.mark.asyncio
async def test_tc00b_adopt_is_idempotent(client: AsyncClient, db_conn, oob_curricula) -> None:
    """TC-00b: Re-adopting the same curriculum returns the existing row (201)."""
    school = await _register(client, "Idempotent Adopt School", "idem-adopt@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r1 = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r1.status_code == 201
    adoption_id_1 = r1.json()["adoption_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r2.status_code == 201
    assert r2.json()["adoption_id"] == adoption_id_1  # same row returned


@pytest.mark.asyncio
async def test_tc00b_adopt_non_platform_curriculum_returns_422(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """TC-00b variant: adopting a non-platform curriculum returns 422."""
    school = await _register(client, "Bad Adopt School", "bad-adopt@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": "nonexistent-curriculum"},
        headers=_auth(token),
    )
    assert r.status_code in (404, 422)


@pytest.mark.asyncio
async def test_tc00b_plain_teacher_cannot_adopt(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """TC-00b variant: plain teacher (not school_admin) cannot adopt a curriculum."""
    school = await _register(client, "Teacher Adopt School", "teacher-adopt@epic12.example.com")
    school_id = school["school_id"]

    teacher_token = make_teacher_token(school_id=school_id, role="teacher")

    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(teacher_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_tc00c_deactivate_adoption(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """TC-00c: school_admin can deactivate an adoption."""
    school = await _register(client, "Deactivate School", "deactivate@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r.status_code == 201
    adoption_id = r.json()["adoption_id"]

    r2 = await client.patch(
        f"/api/v1/schools/{school_id}/library/{adoption_id}",
        json={"status": "deactivated"},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "deactivated"


@pytest.mark.asyncio
async def test_tc00e_two_schools_adopt_same_curriculum(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """TC-00e: Two schools adopting the same OOB curriculum get independent rows."""
    school_a = await _register(client, "Multi Adopt A", "multi-a@epic12.example.com")
    school_b = await _register(client, "Multi Adopt B", "multi-b@epic12.example.com")

    r_a = await client.post(
        f"/api/v1/schools/{school_a['school_id']}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(school_a["access_token"]),
    )
    r_b = await client.post(
        f"/api/v1/schools/{school_b['school_id']}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(school_b["access_token"]),
    )

    assert r_a.status_code == 201
    assert r_b.status_code == 201
    assert r_a.json()["adoption_id"] != r_b.json()["adoption_id"]


@pytest.mark.asyncio
async def test_library_lists_adopted_curricula(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """After adoption, GET /library returns the adopted curriculum."""
    school = await _register(client, "List Library School", "list-lib@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )

    r = await client.get(f"/api/v1/schools/{school_id}/library", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["adoptions"][0]["curriculum_id"] == oob_curricula["curriculum_id"]


# ── TA-2: Import ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tc01_first_import_creates_fork(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """
    TC-01: First unit import creates fork curricula row, updates
    school_adopted_curricula.forked_curriculum_id, upserts
    grade_curriculum_assignments, and creates one unit_content_overrides row.
    """
    school = await _register(client, "Fork School", "fork@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r_adopt = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r_adopt.status_code == 201
    adoption_id = r_adopt.json()["adoption_id"]

    r_import = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_math']}/import",
        headers=_auth(token),
    )
    assert r_import.status_code == 201, r_import.text
    data = r_import.json()

    assert data["fork_created"] is True
    assert data["forked_curriculum_id"] is not None
    assert len(data["overrides"]) >= 1

    lesson_override = next(o for o in data["overrides"] if o["content_type"] == "lesson")
    assert lesson_override["content_source"] == "imported"
    assert lesson_override["review_status"] == "draft"
    assert lesson_override["version_number"] == 1
    assert lesson_override["skipped"] is False

    # Verify library now reflects the fork
    r_lib = await client.get(f"/api/v1/schools/{school_id}/library", headers=_auth(token))
    assert r_lib.status_code == 200
    adoption = r_lib.json()["adoptions"][0]
    assert adoption["forked_curriculum_id"] == data["forked_curriculum_id"]


@pytest.mark.asyncio
async def test_tc02_second_unit_import_reuses_fork(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    tmp_path,
) -> None:
    """TC-02: Second unit import from the same curriculum reuses the existing fork."""
    # Write content for both units
    for unit_id, filename in [
        (oob_curricula["unit_math"], "lesson_en.json"),
        (oob_curricula["unit_sci"], "lesson_en.json"),
    ]:
        lesson_body = {
            "unit_id": unit_id,
            "subject": "Science" if "SCI" in unit_id else "Mathematics",
            "topic": "Unit topic",
            "synopsis": "Test synopsis for unit content.",
            "sections": [{"heading": "Intro", "body": "Content goes here."}],
            "key_points": ["Point A"],
            "learning_objectives": ["Objective A"],
            "reading_level": "Grade 8",
            "estimated_duration_minutes": 30,
            "language": "en",
            "generated_at": "2026-04-01T00:00:00Z",
            "model": "claude-sonnet-4-6",
            "content_version": 1,
        }
        unit_dir = tmp_path / "curricula" / _OOB_CURRICULUM_ID / unit_id
        unit_dir.mkdir(parents=True, exist_ok=True)
        (unit_dir / filename).write_text(json.dumps(lesson_body))

    old_storage = app.state.storage
    app.state.storage = LocalStorage(root=str(tmp_path))
    try:
        school = await _register(client, "Reuse Fork School", "reuse-fork@epic12.example.com")
        school_id, token = school["school_id"], school["access_token"]

        r_adopt = await client.post(
            f"/api/v1/schools/{school_id}/library",
            json={"curriculum_id": oob_curricula["curriculum_id"]},
            headers=_auth(token),
        )
        adoption_id = r_adopt.json()["adoption_id"]

        # First import — creates fork
        r1 = await client.post(
            f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_math']}/import",
            headers=_auth(token),
        )
        assert r1.status_code == 201
        fork_id_1 = r1.json()["forked_curriculum_id"]
        assert r1.json()["fork_created"] is True

        # Second import from same curriculum — reuses fork
        r2 = await client.post(
            f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_sci']}/import",
            headers=_auth(token),
        )
        assert r2.status_code == 201
        assert r2.json()["forked_curriculum_id"] == fork_id_1
        assert r2.json()["fork_created"] is False
    finally:
        app.state.storage = old_storage


@pytest.mark.asyncio
async def test_tc21_reimport_same_unit_returns_skipped(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-21: Re-importing an already-imported unit returns existing rows with skipped=True."""
    school = await _register(client, "Skip School", "skip@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r_adopt = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    adoption_id = r_adopt.json()["adoption_id"]

    unit_id = oob_curricula["unit_math"]
    await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{unit_id}/import",
        headers=_auth(token),
    )

    # Second import of same unit
    r2 = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{unit_id}/import",
        headers=_auth(token),
    )
    assert r2.status_code == 201
    data = r2.json()
    assert all(o["skipped"] for o in data["overrides"])
    assert data["fork_created"] is False


@pytest.mark.asyncio
async def test_tc20_import_not_adopted_returns_404(
    client: AsyncClient, db_conn, oob_curricula, content_store_with_lesson
) -> None:
    """TC-20: Importing from a non-existent adoption_id returns 404."""
    school = await _register(client, "No Adopt School", "no-adopt@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    fake_adoption_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/schools/{school_id}/library/{fake_adoption_id}/units/{oob_curricula['unit_math']}/import",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tc20_import_deactivated_adoption_returns_403(
    client: AsyncClient, db_conn, oob_curricula, content_store_with_lesson
) -> None:
    """TC-20 variant: importing from a deactivated adoption returns 403."""
    school = await _register(client, "Deact Import School", "deact-import@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    adoption_id = r.json()["adoption_id"]

    await client.patch(
        f"/api/v1/schools/{school_id}/library/{adoption_id}",
        json={"status": "deactivated"},
        headers=_auth(token),
    )

    r_import = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_math']}/import",
        headers=_auth(token),
    )
    assert r_import.status_code == 403


# ── TA-3: Edit + governance lifecycle ────────────────────────────────────────


async def _bootstrap_imported_lesson(
    client: AsyncClient,
    school_id: str,
    token: str,
    oob_curricula: dict,
) -> tuple[str, str, str]:
    """
    Register adoption → import unit → return (adoption_id, forked_curriculum_id, override_id).
    Caller must have set up content_store_with_lesson before calling this.
    """
    r = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    assert r.status_code == 201
    adoption_id = r.json()["adoption_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_math']}/import",
        headers=_auth(token),
    )
    assert r2.status_code == 201, r2.text
    fork_id = r2.json()["forked_curriculum_id"]
    lesson = next(o for o in r2.json()["overrides"] if o["content_type"] == "lesson")
    return adoption_id, fork_id, lesson["override_id"]


@pytest.mark.asyncio
async def test_tc06_save_draft_updates_body_in_place(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-06: Saving a draft updates the body in place (same version_number)."""
    n = "Save Draft"
    school = await _register(client, f"{n} School", "save-draft@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, token, oob_curricula)

    new_body = {"sections": [{"heading": "Edited", "body": "Teacher wrote this."}]}
    r = await client.put(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/overrides/lesson",
        json={"body": new_body, "lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["version_number"] == 1  # in-place update, same version
    assert data["review_status"] == "draft"


@pytest.mark.asyncio
async def test_tc09_submit_for_review(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-09: Submitting draft changes review_status to pending_review."""
    school = await _register(client, "Submit Review School", "submit-review@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, token, oob_curricula)

    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["submitted"] == 1
    assert len(data["override_ids"]) == 1


@pytest.mark.asyncio
async def test_tc11_approve_only(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-11: Approve without publish → approved, but not in active versions."""
    school = await _register(client, "Approve Only School", "approve-only@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]
    admin_token = token  # founder is school_admin

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)

    # Submit → pending_review
    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )

    # Approve only (publish=False)
    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/approve",
        json={"lang": "en", "content_type": "lesson", "publish": False},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["approved"] == 1
    assert data["published"] == 0  # not yet active


@pytest.mark.asyncio
async def test_tc10_approve_and_publish(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-10: Approve+publish in one step makes the override active for students."""
    school = await _register(client, "Approve Publish School", "approve-pub@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]
    admin_token = token

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)

    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/approve",
        json={"lang": "en", "content_type": "lesson", "publish": True},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["approved"] == 1
    assert data["published"] == 1  # active version set

    # Unit status should now show is_active=True
    r_status = await client.get(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units",
        headers=_auth(admin_token),
    )
    assert r_status.status_code == 200
    units = r_status.json()["units"]
    math_unit = next((u for u in units if u["unit_id"] == oob_curricula["unit_math"]), None)
    assert math_unit is not None
    lesson_override = next((o for o in math_unit["overrides"] if o["content_type"] == "lesson"), None)
    assert lesson_override is not None
    assert lesson_override["is_active"] is True


@pytest.mark.asyncio
async def test_tc12_reject_with_reason(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-12: Admin rejects pending review with a reason."""
    school = await _register(client, "Reject School", "reject@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]
    admin_token = token

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)

    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/reject",
        json={"lang": "en", "content_type": "lesson", "reason": "Needs more examples."},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["rejected"] == 1


@pytest.mark.asyncio
async def test_tc13_save_after_rejection_creates_new_version(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-13: Saving after rejection creates a new version row (version_number = MAX + 1)."""
    school = await _register(client, "New Version School", "new-ver@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]
    admin_token = token

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)

    unit_id = oob_curricula["unit_math"]

    # Submit → pending_review
    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )

    # Reject
    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/reject",
        json={"lang": "en", "content_type": "lesson", "reason": "Missing worked examples."},
        headers=_auth(admin_token),
    )

    # Save a new draft on the rejected row → creates version 2
    r = await client.put(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/overrides/lesson",
        json={"body": {"sections": [{"heading": "Revised", "body": "Now with more examples."}]}, "lang": "en"},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["version_number"] == 2  # new row, not in-place update
    assert data["review_status"] == "draft"

    # Submit the new version → 1 draft should be submitted
    r2 = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )
    assert r2.status_code == 200
    assert r2.json()["submitted"] == 1


@pytest.mark.asyncio
async def test_save_draft_blocked_when_pending_review(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """Editing content in pending_review state returns 409."""
    school = await _register(client, "Block Edit School", "block-edit@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, token, oob_curricula)
    unit_id = oob_curricula["unit_math"]

    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(token),
    )

    r = await client.put(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/overrides/lesson",
        json={"body": {"sections": [{"heading": "Attempt", "body": "Should be blocked."}]}, "lang": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_submit_with_no_draft_returns_409(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """Submitting when nothing is in draft state returns 409."""
    school = await _register(client, "No Draft School", "no-draft@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, token, oob_curricula)
    unit_id = oob_curricula["unit_math"]

    # Submit once (valid)
    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(token),
    )

    # Submit again (no draft remaining)
    r2 = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(token),
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_publish_approved_separately(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """Approve only, then publish separately — both operations succeed."""
    school = await _register(client, "Batch Publish School", "batch-pub@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]
    admin_token = token

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)
    unit_id = oob_curricula["unit_math"]

    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )
    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/approve",
        json={"lang": "en", "content_type": "lesson", "publish": False},
        headers=_auth(admin_token),
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/publish",
        headers=_auth(admin_token),
        params={"lang": "en", "content_type": "lesson"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_only_admin_can_approve(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """Plain teacher cannot approve — returns 403."""
    school = await _register(client, "Approve RBAC School", "approve-rbac@epic12.example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    teacher_token = make_teacher_token(school_id=school_id, role="teacher")

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, admin_token, oob_curricula)
    unit_id = oob_curricula["unit_math"]

    await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/review",
        json={"lang": "en", "content_type": "lesson"},
        headers=_auth(admin_token),
    )

    r = await client.post(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{unit_id}/approve",
        json={"lang": "en", "content_type": "lesson", "publish": True},
        headers=_auth(teacher_token),
    )
    assert r.status_code == 403


# ── TA-4: Pipeline guard ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_guard_returns_schools_with_overrides(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """check_school_overrides returns school_ids that have overrides for a unit."""
    from pipeline.guard import check_school_overrides

    school = await _register(client, "Guard School", "guard@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    r_adopt = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": oob_curricula["curriculum_id"]},
        headers=_auth(token),
    )
    adoption_id = r_adopt.json()["adoption_id"]

    await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/{oob_curricula['unit_math']}/import",
        headers=_auth(token),
    )

    # Guard must run via a bypass connection (same pattern as pipeline)
    conn = await asyncpg.connect(_TEST_DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    try:
        schools = await check_school_overrides(
            conn,
            oob_curricula["curriculum_id"],
            oob_curricula["unit_math"],
            "en",
        )
        assert school_id in schools
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_pipeline_guard_empty_when_no_overrides(db_conn, oob_curricula) -> None:
    """check_school_overrides returns [] when no school has overrides for this unit."""
    from pipeline.guard import check_school_overrides

    conn = await asyncpg.connect(_TEST_DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
    try:
        # Use a unit that definitely has no overrides in this test run
        schools = await check_school_overrides(
            conn,
            _OOB_CURRICULUM_ID,
            "test-unit-that-was-never-imported",
            "en",
        )
        assert schools == []
    finally:
        await conn.close()


# ── Security: cross-school access ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_from_other_school_cannot_list_library(
    client: AsyncClient, db_conn, oob_curricula
) -> None:
    """Teacher from a different school cannot list another school's library."""
    school = await _register(client, "Cross School A", "cross-a@epic12.example.com")
    school_id = school["school_id"]

    wrong_token = make_teacher_token(school_id=str(uuid.uuid4()), role="school_admin")
    r = await client.get(f"/api/v1/schools/{school_id}/library", headers=_auth(wrong_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_teacher_from_other_school_cannot_save_draft(
    client: AsyncClient,
    db_conn,
    oob_curricula,
    content_store_with_lesson,
) -> None:
    """TC-19: A teacher from School B cannot call save_draft on School A's fork."""
    school = await _register(client, "RLS School A", "rls-a@epic12.example.com")
    school_id, token = school["school_id"], school["access_token"]

    _, fork_id, _ = await _bootstrap_imported_lesson(client, school_id, token, oob_curricula)

    # Token from a different school
    other_token = make_teacher_token(school_id=str(uuid.uuid4()), role="school_admin")

    r = await client.put(
        f"/api/v1/schools/{school_id}/content/{fork_id}/units/{oob_curricula['unit_math']}/overrides/lesson",
        json={"body": {"sections": [{"heading": "Hack", "body": "School B write attempt."}]}, "lang": "en"},
        headers=_auth(other_token),
    )
    assert r.status_code == 403
