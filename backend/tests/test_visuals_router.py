"""
Integration tests for backend/src/visuals/router.py — issue #318 phase 2b.

Covers:
  POST   /api/v1/schools/{school_id}/visuals/upload
  GET    /api/v1/schools/{school_id}/visuals
  DELETE /api/v1/schools/{school_id}/visuals/{asset_path}

Uses LocalVisualStorage backed by a tmp_path so no S3 / live infra is needed.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

from src.visuals.storage import _reset_backend_for_tests
from tests.helpers.token_factory import make_teacher_token


@pytest.fixture
def visuals_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Configure the visual storage backend to write under tmp_path."""
    monkeypatch.setenv("VISUAL_STORAGE_BACKEND", "local")
    monkeypatch.setenv("VISUAL_STORAGE_LOCAL_PATH", str(tmp_path))
    monkeypatch.setenv("VISUAL_STORAGE_PUBLIC_BASE_URL", "/sample-visuals")
    _reset_backend_for_tests()
    yield tmp_path
    _reset_backend_for_tests()


def _svg_payload() -> bytes:
    return b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5"/></svg>'


# ── upload ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_svg_succeeds(client: AsyncClient, visuals_root: Path):
    school_id = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_id, role="teacher")
    files = {"file": ("xt-uam.svg", io.BytesIO(_svg_payload()), "image/svg+xml")}
    data = {
        "curriculum_id": "default-2026-g11-science",
        "unit_id": "G11-PHYS-002",
        "section_id": "s2",
    }
    res = await client.post(
        f"/api/v1/schools/{school_id}/visuals/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["bytes"] == len(_svg_payload())
    assert body["content_type"] == "image/svg+xml"
    assert body["path"].startswith(f"{school_id}/default-2026-g11-science/G11-PHYS-002/s2/")
    assert body["path"].endswith(".svg")
    assert body["url"].startswith("/sample-visuals/")


@pytest.mark.asyncio
async def test_upload_rejects_unknown_mime(client: AsyncClient, visuals_root: Path):
    school_id = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_id, role="teacher")
    files = {"file": ("evil.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-dosexec")}
    data = {"curriculum_id": "c", "unit_id": "u", "section_id": "s1"}
    res = await client.post(
        f"/api/v1/schools/{school_id}/visuals/upload",
        files=files, data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(client: AsyncClient, visuals_root: Path):
    school_id = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_id, role="teacher")
    files = {"file": ("empty.svg", io.BytesIO(b""), "image/svg+xml")}
    data = {"curriculum_id": "c", "unit_id": "u", "section_id": "s1"}
    res = await client.post(
        f"/api/v1/schools/{school_id}/visuals/upload",
        files=files, data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_other_school(client: AsyncClient, visuals_root: Path):
    """Teacher from school A cannot upload to school B."""
    school_a = str(uuid.uuid4())
    school_b = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_a, role="teacher")
    files = {"file": ("x.svg", io.BytesIO(_svg_payload()), "image/svg+xml")}
    data = {"curriculum_id": "c", "unit_id": "u", "section_id": "s1"}
    res = await client.post(
        f"/api/v1/schools/{school_b}/visuals/upload",
        files=files, data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


# ── list ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_uploaded_assets(client: AsyncClient, visuals_root: Path):
    school_id = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_id, role="teacher")
    headers = {"Authorization": f"Bearer {token}"}

    # Upload two assets
    for sec in ("s1", "s2"):
        await client.post(
            f"/api/v1/schools/{school_id}/visuals/upload",
            files={"file": (f"{sec}.svg", io.BytesIO(_svg_payload()), "image/svg+xml")},
            data={"curriculum_id": "c1", "unit_id": "u1", "section_id": sec},
            headers=headers,
        )

    res = await client.get(
        f"/api/v1/schools/{school_id}/visuals",
        params={"curriculum_id": "c1", "unit_id": "u1"},
        headers=headers,
    )
    assert res.status_code == 200
    assets = res.json()["assets"]
    assert len(assets) == 2
    paths = [a["path"] for a in assets]
    assert any("/s1/" in p for p in paths)
    assert any("/s2/" in p for p in paths)
    assert all(a["url"].startswith("/sample-visuals/") for a in assets)


# ── delete ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_asset(client: AsyncClient, visuals_root: Path):
    school_id = str(uuid.uuid4())
    token = make_teacher_token(school_id=school_id, role="teacher")
    headers = {"Authorization": f"Bearer {token}"}

    up = await client.post(
        f"/api/v1/schools/{school_id}/visuals/upload",
        files={"file": ("x.svg", io.BytesIO(_svg_payload()), "image/svg+xml")},
        data={"curriculum_id": "c", "unit_id": "u", "section_id": "s1"},
        headers=headers,
    )
    asset_path = up.json()["path"]

    # Delete succeeds
    res = await client.delete(
        f"/api/v1/schools/{school_id}/visuals/{asset_path}",
        headers=headers,
    )
    assert res.status_code == 204

    # Re-delete: 404
    res2 = await client.delete(
        f"/api/v1/schools/{school_id}/visuals/{asset_path}",
        headers=headers,
    )
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_delete_rejects_other_schools_asset(client: AsyncClient, visuals_root: Path):
    school_a = str(uuid.uuid4())
    school_b = str(uuid.uuid4())
    token_b = make_teacher_token(school_id=school_b, role="teacher")
    # Asset path begins with school_a; token belongs to school_b
    bad_path = f"{school_a}/c/u/s/x.svg"
    res = await client.delete(
        f"/api/v1/schools/{school_b}/visuals/{bad_path}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # 403 — the path-prefix guard catches it before storage
    assert res.status_code == 403
