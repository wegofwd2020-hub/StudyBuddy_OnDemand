"""
Happy-path integration test for PUT /api/v1/schools/{school_id}/visuals/sections.

Issue #318 phase 2c-2 follow-up. Reuses Epic 12's fixture pattern (school
register → adopt OOB curriculum → import unit → override row exists),
then exercises the visual-block PUT against the resulting tutorial draft
and verifies a new override row was inserted with the modified body.

Kept in its own file so the existing test_visuals_router suite stays
storage-only and doesn't pull in the test DB setup.
"""

from __future__ import annotations

import json
import os
import sys

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app

from src.core.storage import LocalStorage

# Make the pipeline package importable (matches test_epic12 pattern)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Test DB URL (mirrors conftest)
_dev_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
_TEST_DB_URL = os.environ.get(
    "TEST_DB_URL",
    _dev_db_url.replace("/studybuddy", "/studybuddy_test").replace(
        "@pgbouncer:", "@db:"
    ),
)

# Fixed test IDs — disjoint from epic12's IDs to avoid cross-test interference
_OOB_CURRICULUM_ID = "test-oob-g11-visuals-happypath"
_OOB_UNIT_ID = "test-oob-g11-visuals-happypath-PHYS-U01"

_PW = "SecureTestPwd1!"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": name,
            "contact_email": email,
            "country": "CA",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Session fixture: insert the OOB curriculum + unit ────────────────────────


@pytest_asyncio.fixture(scope="session")
async def visuals_oob_curriculum():
    """Seed an OOB curriculum + unit row in the test DB."""
    conn = await asyncpg.connect(_TEST_DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    await conn.execute(
        """
        INSERT INTO curricula
            (curriculum_id, name, grade, year, is_default,
             owner_type, status, source_type, retention_status)
        VALUES ($1, $2, 11, 2026, TRUE, 'platform', 'active', 'default', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _OOB_CURRICULUM_ID,
        "Grade 11 Visuals Test",
    )
    await conn.execute(
        """
        INSERT INTO curriculum_units
            (unit_id, curriculum_id, subject, title, unit_name, has_lab, sort_order)
        VALUES ($1, $2, 'PHYS', 'Visual Test Unit', 'Visual Test Unit', FALSE, 0)
        ON CONFLICT DO NOTHING
        """,
        _OOB_UNIT_ID,
        _OOB_CURRICULUM_ID,
    )

    await conn.close()
    yield {
        "curriculum_id": _OOB_CURRICULUM_ID,
        "unit_id": _OOB_UNIT_ID,
    }


# ── Per-test fixture: write tutorial_en.json + lesson_en.json into content store


@pytest.fixture()
def visuals_content_store(tmp_path):
    """
    Point app.state.storage at a tmp LocalStorage that has tutorial_en.json
    (and a stub lesson_en.json) for the visuals test unit. The import_unit
    endpoint probes the content store and creates an override per type found.
    """
    tutorial_body = {
        "unit_id": _OOB_UNIT_ID,
        "language": "en",
        "title": "Visual Test Tutorial",
        "sections": [
            {
                "section_id": "s1",
                "title": "First Section",
                "content": "Body of section 1.",
                "examples": ["Example 1"],
                "practice_question": "Practice 1?",
                "visuals": [],
            },
            {
                "section_id": "s2",
                "title": "Second Section",
                "content": "Body of section 2.",
                "examples": ["Example 2"],
                "practice_question": "Practice 2?",
                "visuals": [],
            },
        ],
        "common_mistakes": ["A common mistake."],
        "generated_at": "2026-04-01T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    lesson_body = {
        "unit_id": _OOB_UNIT_ID,
        "subject": "Physics",
        "topic": "Visuals test",
        "synopsis": "Stub.",
        "sections": [{"heading": "Intro", "body": "."}],
        "key_points": ["x"],
        "learning_objectives": ["y"],
        "reading_level": "Grade 11",
        "estimated_duration_minutes": 30,
        "language": "en",
        "generated_at": "2026-04-01T00:00:00Z",
        "model": "claude-sonnet-4-6",
        "content_version": 1,
    }
    unit_dir = tmp_path / "curricula" / _OOB_CURRICULUM_ID / _OOB_UNIT_ID
    unit_dir.mkdir(parents=True)
    (unit_dir / "tutorial_en.json").write_text(json.dumps(tutorial_body))
    (unit_dir / "lesson_en.json").write_text(json.dumps(lesson_body))

    old_storage = app.state.storage
    app.state.storage = LocalStorage(root=str(tmp_path))
    yield tmp_path
    app.state.storage = old_storage


# ── The test ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_section_visuals_happy_path(
    client: AsyncClient,
    db_conn,
    visuals_oob_curriculum,
    visuals_content_store,
) -> None:
    """
    Full Phase D round-trip:
      1. Register school.
      2. Adopt the OOB curriculum.
      3. Import the unit (creates fork + override rows for tutorial + lesson).
      4. PUT new visuals[] for section s1.
      5. Assert: response carries new override_id, version_number=2,
         status=draft.
      6. GET via list_section_visuals should reflect the new visuals on s1
         and leave s2 alone.
    """
    school = await _register(
        client,
        "Visuals Happy Path School",
        "visuals-happy@epic318.example.com",
    )
    school_id, token = school["school_id"], school["access_token"]

    # 1. Adopt
    r_adopt = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": visuals_oob_curriculum["curriculum_id"]},
        headers=_auth(token),
    )
    assert r_adopt.status_code == 201, r_adopt.text
    adoption_id = r_adopt.json()["adoption_id"]

    # 2. Import the unit — creates fork + tutorial override v1
    r_import = await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/"
        f"{visuals_oob_curriculum['unit_id']}/import",
        headers=_auth(token),
    )
    assert r_import.status_code == 201, r_import.text
    overrides = r_import.json()["overrides"]
    tutorial_overrides = [o for o in overrides if o["content_type"] == "tutorial"]
    assert len(tutorial_overrides) == 1
    assert tutorial_overrides[0]["version_number"] == 1
    assert tutorial_overrides[0]["review_status"] == "draft"

    # 3. PUT new visuals[] for section s1
    new_blocks = [
        {
            "kind": "image-grid",
            "heading": "Test Venn diagrams",
            "items": [
                {
                    "src": "/visuals/_legacy/test/union.svg",
                    "alt": "Union",
                    "caption": "A ∪ B",
                },
                {
                    "src": "/visuals/_legacy/test/intersection.svg",
                    "alt": "Intersection",
                    "caption": "A ∩ B",
                },
            ],
        },
        {
            "kind": "video",
            "heading": "Watch",
            "items": [
                {
                    "src": "/visuals/_legacy/test/clip.mp4",
                    "alt": "Test clip",
                    "duration": "0:10",
                }
            ],
        },
    ]
    r_put = await client.put(
        f"/api/v1/schools/{school_id}/visuals/sections",
        json={
            "adoption_id": adoption_id,
            "unit_id": visuals_oob_curriculum["unit_id"],
            "section_id": "s1",
            "visuals": new_blocks,
        },
        headers=_auth(token),
    )
    assert r_put.status_code == 200, r_put.text
    put_resp = r_put.json()
    assert put_resp["version_number"] == 2
    assert put_resp["review_status"] == "draft"
    assert "override_id" in put_resp

    # 4. GET back — confirm the new visuals landed on s1, s2 unchanged
    r_list = await client.get(
        f"/api/v1/schools/{school_id}/visuals/sections",
        params={
            "adoption_id": adoption_id,
            "unit_id": visuals_oob_curriculum["unit_id"],
        },
        headers=_auth(token),
    )
    assert r_list.status_code == 200, r_list.text
    list_resp = r_list.json()
    assert list_resp["override_version"] == 2
    assert list_resp["override_status"] == "draft"

    def _strip_none(obj):
        """Recursively drop keys whose value is None — Pydantic emits all
        optional fields, but the test inputs only included populated ones."""
        if isinstance(obj, dict):
            return {k: _strip_none(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [_strip_none(x) for x in obj]
        return obj

    sections_by_id = {s["section_id"]: s for s in list_resp["sections"]}
    assert _strip_none(sections_by_id["s1"]["visuals"]) == new_blocks
    assert sections_by_id["s2"]["visuals"] == []

    # 5. Idempotent re-PUT lands a v3 (append-only versioning)
    r_put2 = await client.put(
        f"/api/v1/schools/{school_id}/visuals/sections",
        json={
            "adoption_id": adoption_id,
            "unit_id": visuals_oob_curriculum["unit_id"],
            "section_id": "s1",
            "visuals": [],  # clear out
        },
        headers=_auth(token),
    )
    assert r_put2.status_code == 200, r_put2.text
    assert r_put2.json()["version_number"] == 3

    r_list_after = await client.get(
        f"/api/v1/schools/{school_id}/visuals/sections",
        params={
            "adoption_id": adoption_id,
            "unit_id": visuals_oob_curriculum["unit_id"],
        },
        headers=_auth(token),
    )
    assert r_list_after.json()["override_version"] == 3
    sections_by_id_after = {
        s["section_id"]: s for s in r_list_after.json()["sections"]
    }
    assert sections_by_id_after["s1"]["visuals"] == []


@pytest.mark.asyncio
async def test_put_section_visuals_wrong_section_id_returns_404(
    client: AsyncClient,
    db_conn,
    visuals_oob_curriculum,
    visuals_content_store,
) -> None:
    """A PUT against a section that doesn't exist in the tutorial returns 404."""
    school = await _register(
        client,
        "Visuals 404 School",
        "visuals-404@epic318.example.com",
    )
    school_id, token = school["school_id"], school["access_token"]

    r_adopt = await client.post(
        f"/api/v1/schools/{school_id}/library",
        json={"curriculum_id": visuals_oob_curriculum["curriculum_id"]},
        headers=_auth(token),
    )
    adoption_id = r_adopt.json()["adoption_id"]
    await client.post(
        f"/api/v1/schools/{school_id}/library/{adoption_id}/units/"
        f"{visuals_oob_curriculum['unit_id']}/import",
        headers=_auth(token),
    )

    r_bad = await client.put(
        f"/api/v1/schools/{school_id}/visuals/sections",
        json={
            "adoption_id": adoption_id,
            "unit_id": visuals_oob_curriculum["unit_id"],
            "section_id": "section-that-does-not-exist",
            "visuals": [
                {"kind": "image", "items": [{"src": "/x.svg", "alt": "x"}]}
            ],
        },
        headers=_auth(token),
    )
    assert r_bad.status_code == 404
    assert "not found" in r_bad.json()["detail"].lower()
