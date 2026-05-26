"""
Endpoint + service tests for the Curriculum Authoring Studio (PR-A).

Covers the super-admin gate, project creation, analyze dispatch, the
run_analysis worker body, structure editing, and materialisation into a
staged platform curriculum.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from main import app

from src.admin import authoring_service as svc

# run_analysis() lazily imports the `pipeline` package (repo root). CI runs
# pytest from backend/, so ensure repo root is importable before any test runs.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── Fake provider returning structure JSON or flow JSON by prompt marker ──────


class _DualFakeProvider:
    """Branches on the prompt: structurer prompt vs flow-analyzer prompt."""

    STRUCTURED = {
        "subjects": [{
            "subject_label": "Physics",
            "units": [
                {"title": "Kinematics", "subtopics": ["Speed", "Velocity"],
                 "prerequisites": []},
                {"title": "Dynamics", "subtopics": ["Forces"],
                 "prerequisites": ["Kinematics"]},
            ],
        }]
    }
    FLOW = {"summary": "Flow looks sound.", "warnings": []}

    def generate(self, prompt: str) -> tuple[str, int, int]:
        if "pedagogy reviewer" in prompt:
            return json.dumps(self.FLOW), 50, 60
        return json.dumps(self.STRUCTURED), 80, 120


async def _seed_analyzed_project(
    *, title: str = "Grade 9 Physics", grade: int | None = 9
) -> str:
    """Create + analyse a project on the committed app pool so HTTP endpoints
    (which use their own pooled connection) can see it."""
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        project = await svc.create_project(
            conn,
            title=title,
            grade=grade,
            languages=["en"],
            raw_toc="1. Kinematics\n2. Dynamics",
            created_by=None,
        )
        await svc.run_analysis(conn, project["project_id"], provider=_DualFakeProvider())
    return project["project_id"]


# ── Gate ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_requires_super_admin(
    client: AsyncClient, product_admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/admin/authoring/projects",
        headers={"Authorization": f"Bearer {product_admin_token}"},
        json={"title": "G9 Physics", "grade": 9, "languages": ["en"],
              "raw_toc": "1. Motion\n2. Forces"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_project_super_admin_ok(
    client: AsyncClient, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/admin/authoring/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "G9 Physics", "grade": 9, "languages": ["en"],
              "raw_toc": "1. Motion\n2. Forces"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "draft"
    assert body["project_id"]


@pytest.mark.asyncio
async def test_create_project_rejects_bad_language(
    client: AsyncClient, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/admin/authoring/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "X", "grade": 9, "languages": ["klingon"], "raw_toc": "x"},
    )
    assert r.status_code == 422


# ── Analyze dispatch ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_dispatches_and_marks_analyzing(
    client: AsyncClient, admin_token: str
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await client.post(
        "/api/v1/admin/authoring/projects",
        headers=headers,
        json={"title": "G9 Physics", "grade": 9, "languages": ["en"],
              "raw_toc": "1. Kinematics\n2. Dynamics"},
    )
    project_id = created.json()["project_id"]

    with patch("src.core.celery_app.celery_app.send_task") as send_task:
        r = await client.post(
            f"/api/v1/admin/authoring/projects/{project_id}/analyze", headers=headers
        )
    assert r.status_code == 202
    assert r.json()["status"] == "analyzing"
    send_task.assert_called_once()

    detail = await client.get(
        f"/api/v1/admin/authoring/projects/{project_id}", headers=headers
    )
    assert detail.json()["status"] == "analyzing"


@pytest.mark.asyncio
async def test_analyze_missing_project_404(
    client: AsyncClient, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/admin/authoring/projects/00000000-0000-0000-0000-000000000000/analyze",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


# ── run_analysis worker body (direct, with fake provider) ─────────────────────


@pytest.mark.asyncio
async def test_run_analysis_structures_and_flows(client: AsyncClient) -> None:
    # Use a pooled connection (jsonb codec installed) — the raw db_conn fixture
    # cannot bind dicts to jsonb columns.
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        project = await svc.create_project(
            conn,
            title="G9 Physics",
            grade=9,
            languages=["en"],
            raw_toc="1. Kinematics\n2. Dynamics",
            created_by=None,
        )
        await svc.run_analysis(conn, project["project_id"], provider=_DualFakeProvider())
        detail = await svc.get_project(conn, project["project_id"])

    assert detail["status"] == "analyzed"
    assert detail["structured_toc"]["subjects"][0]["units"][0]["title"] == "Kinematics"
    assert detail["flow_report"]["summary"] == "Flow looks sound."


@pytest.mark.asyncio
async def test_run_analysis_records_error_on_bad_toc(client: AsyncClient) -> None:
    class _BadProvider:
        def generate(self, prompt: str) -> tuple[str, int, int]:
            return "this is not json", 1, 1

    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        project = await svc.create_project(
            conn, title="X", grade=None, languages=["en"], raw_toc="junk", created_by=None
        )
        await svc.run_analysis(conn, project["project_id"], provider=_BadProvider())
        detail = await svc.get_project(conn, project["project_id"])

    assert detail["status"] == "draft"
    assert detail["analyze_error"]


# ── Structure edit ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_edit_structure_persists(client: AsyncClient, admin_token: str) -> None:
    project_id = await _seed_analyzed_project()
    edited = {"subjects": [{"subject_label": "Physics", "units": [
        {"title": "Kinematics", "subtopics": ["Speed", "Velocity", "Acceleration"],
         "prerequisites": []},
    ]}]}
    r = await client.put(
        f"/api/v1/admin/authoring/projects/{project_id}/structure",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"structured_toc": edited},
    )
    assert r.status_code == 200
    units = r.json()["structured_toc"]["subjects"][0]["units"]
    assert units[0]["subtopics"] == ["Speed", "Velocity", "Acceleration"]


@pytest.mark.asyncio
async def test_edit_structure_conflict_when_draft(
    client: AsyncClient, admin_token: str
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await client.post(
        "/api/v1/admin/authoring/projects",
        headers=headers,
        json={"title": "X", "grade": 9, "languages": ["en"], "raw_toc": "1. A"},
    )
    project_id = created.json()["project_id"]
    r = await client.put(
        f"/api/v1/admin/authoring/projects/{project_id}/structure",
        headers=headers,
        json={"structured_toc": {"subjects": [
            {"subject_label": "S", "units": [{"title": "A"}]}]}},
    )
    assert r.status_code == 409


# ── Materialize ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_materialize_creates_staged_platform_curriculum(
    client: AsyncClient, admin_token: str, db_conn
) -> None:
    project_id = await _seed_analyzed_project()
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{project_id}/materialize",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201
    curriculum_id = r.json()["curriculum_id"]
    assert r.json()["units_created"] == 2

    row = await db_conn.fetchrow(
        "SELECT owner_type, source_type, is_default, school_id "
        "FROM curricula WHERE curriculum_id = $1",
        curriculum_id,
    )
    assert row["owner_type"] == "platform"
    assert row["source_type"] == "admin_authored"
    assert row["is_default"] is False
    assert row["school_id"] is None

    units = await db_conn.fetch(
        "SELECT title, unit_name FROM curriculum_units WHERE curriculum_id = $1",
        curriculum_id,
    )
    assert len(units) == 2
    # pitfall #20 — unit_name mirrors title and is never null
    assert all(u["unit_name"] == u["title"] for u in units)


@pytest.mark.asyncio
async def test_materialize_is_idempotent(
    client: AsyncClient, admin_token: str
) -> None:
    project_id = await _seed_analyzed_project()
    headers = {"Authorization": f"Bearer {admin_token}"}
    first = await client.post(
        f"/api/v1/admin/authoring/projects/{project_id}/materialize", headers=headers
    )
    second = await client.post(
        f"/api/v1/admin/authoring/projects/{project_id}/materialize", headers=headers
    )
    assert first.json()["curriculum_id"] == second.json()["curriculum_id"]
    assert second.json()["units_created"] == 2


@pytest.mark.asyncio
async def test_materialize_conflict_without_structure(
    client: AsyncClient, admin_token: str
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await client.post(
        "/api/v1/admin/authoring/projects",
        headers=headers,
        json={"title": "X", "grade": 9, "languages": ["en"], "raw_toc": "1. A"},
    )
    project_id = created.json()["project_id"]
    r = await client.post(
        f"/api/v1/admin/authoring/projects/{project_id}/materialize", headers=headers
    )
    assert r.status_code == 409
