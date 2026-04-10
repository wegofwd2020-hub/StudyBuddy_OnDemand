"""
tests/test_admin_warnings.py

Tests for AlexJS warning acknowledgement endpoints (GitHub issue #76).

Coverage:
  - GET  /admin/content/review/{version_id}/warnings
      · returns empty list when no warnings in meta.json
      · returns warnings with acknowledged=False when no acks
      · returns acknowledged=True after POST acknowledge
      · returns 404 for unknown version_id
  - POST /admin/content/review/{version_id}/warnings/{unit}/{ct}/{idx}/acknowledge
      · idempotent — re-POSTing updates is_false_positive
      · requires review:approve permission (tester role → 403)
  - POST /admin/content/review/{version_id}/approve
      · blocked (422) when alex_warnings_count > 0 and zero acks exist
      · succeeds when all warnings are acknowledged
      · succeeds when alex_warnings_count == 0 (no ack required)
"""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient

from main import app
from src.core.storage import LocalStorage
from tests.helpers.token_factory import make_admin_token

# ── Fixed IDs ─────────────────────────────────────────────────────────────────

_ADMIN_ID = "00000000-0000-0000-0000-000000000099"
_UNIT_ID = "G8-MATH-001"
_CURRICULUM_ID = "default-2026-g8"
_SUBJECT = "Mathematics"


def _hdrs(role: str = "super_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=_ADMIN_ID, role=role)}"}


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _ensure_admin(client: AsyncClient) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, role, password_hash)
        VALUES ($1, 'warn-admin@test.invalid', 'super_admin', 'x')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(_ADMIN_ID),
    )


async def _ensure_curricula(client: AsyncClient) -> None:
    """Insert the default-2026-g8 curricula row (required FK for curriculum_units)."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO curricula
            (curriculum_id, grade, year, name, is_default, source_type,
             status, owner_type, retention_status)
        VALUES ($1, 8, 2026, 'Default Grade 8 (2026)', true, 'default',
                'active', 'platform', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        _CURRICULUM_ID,
    )


async def _insert_version(
    client: AsyncClient,
    warnings_count: int = 0,
) -> tuple[str, str, str]:
    """Insert a content version row; return (version_id, subject, unit_id)."""
    pool = client._transport.app.state.pool
    subj = f"Warn-{uuid.uuid4().hex[:8]}"
    unit_id = f"G8-WARN-{uuid.uuid4().hex[:6].upper()}"
    row = await pool.fetchrow(
        """
        INSERT INTO content_subject_versions
            (curriculum_id, subject, version_number, status, alex_warnings_count)
        VALUES ($1, $2, 1, 'ready_for_review', $3)
        RETURNING version_id::text
        """,
        _CURRICULUM_ID,
        subj,
        warnings_count,
    )
    return row["version_id"], subj, unit_id


async def _ensure_unit(client: AsyncClient, subject: str, unit_id: str) -> None:
    """Insert a curriculum_units row (requires _ensure_curricula first)."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO curriculum_units
            (curriculum_id, subject, unit_id, unit_name, title, sort_order)
        VALUES ($1, $2, $3, $3, $3, 1)
        ON CONFLICT DO NOTHING
        """,
        _CURRICULUM_ID,
        subject,
        unit_id,
    )


def _meta_json(unit_id: str, warnings: list[dict]) -> str:
    """Build a meta.json with full warning detail."""
    return json.dumps(
        {
            "unit_id": unit_id,
            "curriculum_id": _CURRICULUM_ID,
            "langs_built": ["en"],
            "content_version": 1,
            "model": "claude-sonnet-4-6",
            "alex_warnings_count": len(warnings),
            "alex_warnings_by_type": {"lesson": len(warnings)} if warnings else {},
            "alex_warnings_detail_by_type": {"lesson": warnings} if warnings else {},
        }
    )


# ── GET /warnings ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_warnings_empty_when_no_meta(client, tmp_path):
    """Returns total_count=0 when meta.json has no detail (older units)."""
    await _ensure_admin(client)
    vid, _, _ = await _insert_version(client, warnings_count=0)

    # No meta.json written — storage returns exists=False, warnings list is empty.
    app.state.storage = LocalStorage(root=str(tmp_path))
    r = await client.get(
        f"/api/v1/admin/content/review/{vid}/warnings",
        headers=_hdrs(),
    )

    assert r.status_code == 200
    data = r.json()
    assert data["version_id"] == vid
    assert data["total_count"] == 0
    assert data["unacknowledged_count"] == 0
    assert data["warnings"] == []


@pytest.mark.asyncio
async def test_get_warnings_returns_unacked_warnings(client, tmp_path):
    """Warnings from meta.json are returned with acknowledged=False."""
    await _ensure_admin(client)
    await _ensure_curricula(client)
    vid, subj, unit_id = await _insert_version(client, warnings_count=2)
    await _ensure_unit(client, subj, unit_id)

    unit_dir = tmp_path / "curricula" / _CURRICULUM_ID / unit_id
    unit_dir.mkdir(parents=True)
    (unit_dir / "meta.json").write_text(
        _meta_json(unit_id, [
            {"line": 1, "column": 5, "message": "Don't use \"crazy\""},
            {"line": 3, "column": 10, "message": "Avoid \"mankind\""},
        ])
    )

    app.state.storage = LocalStorage(root=str(tmp_path))
    r = await client.get(
        f"/api/v1/admin/content/review/{vid}/warnings",
        headers=_hdrs(),
    )

    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 2
    assert data["unacknowledged_count"] == 2
    warnings = data["warnings"]
    assert len(warnings) == 2
    assert warnings[0]["acknowledged"] is False
    assert warnings[0]["content_type"] == "lesson"
    assert "crazy" in warnings[0]["message"]


@pytest.mark.asyncio
async def test_get_warnings_404_on_unknown_version(client):
    """Returns 404 for a version_id that does not exist."""
    await _ensure_admin(client)
    fake_id = str(uuid.uuid4())

    r = await client.get(
        f"/api/v1/admin/content/review/{fake_id}/warnings",
        headers=_hdrs(),
    )
    assert r.status_code == 404


# ── POST /warnings/.../acknowledge ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_acknowledge_warning_marks_acknowledged(client, tmp_path):
    """After POST acknowledge, GET warnings returns acknowledged=True."""
    await _ensure_admin(client)
    await _ensure_curricula(client)
    vid, subj, unit_id = await _insert_version(client, warnings_count=1)
    await _ensure_unit(client, subj, unit_id)

    unit_dir = tmp_path / "curricula" / _CURRICULUM_ID / unit_id
    unit_dir.mkdir(parents=True)
    (unit_dir / "meta.json").write_text(
        _meta_json(unit_id, [{"line": 2, "column": 1, "message": "Don't use \"lame\""}])
    )

    app.state.storage = LocalStorage(root=str(tmp_path))

    ack_r = await client.post(
        f"/api/v1/admin/content/review/{vid}/warnings/{unit_id}/lesson/0/acknowledge",
        json={"is_false_positive": False},
        headers=_hdrs(),
    )
    assert ack_r.status_code == 200
    ack_data = ack_r.json()
    assert ack_data["is_false_positive"] is False
    assert ack_data["unit_id"] == unit_id
    assert ack_data["warning_index"] == 0

    get_r = await client.get(
        f"/api/v1/admin/content/review/{vid}/warnings",
        headers=_hdrs(),
    )

    assert get_r.status_code == 200
    data = get_r.json()
    assert data["unacknowledged_count"] == 0
    assert data["warnings"][0]["acknowledged"] is True


@pytest.mark.asyncio
async def test_acknowledge_warning_idempotent(client, tmp_path):
    """Re-POSTing acknowledge updates is_false_positive without creating duplicate rows."""
    await _ensure_admin(client)
    await _ensure_curricula(client)
    vid, subj, unit_id = await _insert_version(client, warnings_count=1)
    await _ensure_unit(client, subj, unit_id)

    unit_dir = tmp_path / "curricula" / _CURRICULUM_ID / unit_id
    unit_dir.mkdir(parents=True)
    (unit_dir / "meta.json").write_text(
        _meta_json(unit_id, [{"line": 1, "column": 1, "message": "Avoid gendered term"}])
    )

    url = f"/api/v1/admin/content/review/{vid}/warnings/{unit_id}/lesson/0/acknowledge"

    app.state.storage = LocalStorage(root=str(tmp_path))

    r1 = await client.post(url, json={"is_false_positive": False}, headers=_hdrs())
    assert r1.status_code == 200

    # Re-submit as false positive
    r2 = await client.post(url, json={"is_false_positive": True}, headers=_hdrs())
    assert r2.status_code == 200
    assert r2.json()["is_false_positive"] is True

    pool = client._transport.app.state.pool
    count = await pool.fetchval(
        "SELECT COUNT(*) FROM content_warning_acks WHERE version_id = $1",
        uuid.UUID(vid),
    )
    assert count == 1


@pytest.mark.asyncio
async def test_acknowledge_requires_review_approve_permission(client):
    """tester role (review:read only) cannot POST acknowledge."""
    await _ensure_admin(client)
    vid, _, unit_id = await _insert_version(client, warnings_count=1)

    r = await client.post(
        f"/api/v1/admin/content/review/{vid}/warnings/{unit_id}/lesson/0/acknowledge",
        json={"is_false_positive": False},
        headers=_hdrs(role="tester"),
    )
    assert r.status_code == 403


# ── Approve gate ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_blocked_when_warnings_unacknowledged(client):
    """POST approve returns 422 when alex_warnings_count > 0 and no acks exist."""
    await _ensure_admin(client)
    vid, _, _ = await _insert_version(client, warnings_count=3)

    r = await client.post(
        f"/api/v1/admin/content/review/{vid}/approve",
        json={},
        headers=_hdrs(),
    )
    assert r.status_code == 422
    assert "AlexJS" in r.json()["detail"]


@pytest.mark.asyncio
async def test_approve_succeeds_after_all_warnings_acknowledged(client):
    """POST approve returns 200 once at least one ack exists for the version."""
    await _ensure_admin(client)
    vid, _, unit_id = await _insert_version(client, warnings_count=1)

    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO content_warning_acks
            (version_id, unit_id, content_type, warning_index, is_false_positive, acknowledged_by)
        VALUES ($1, $2, 'lesson', 0, false, $3)
        ON CONFLICT DO NOTHING
        """,
        uuid.UUID(vid),
        unit_id,
        uuid.UUID(_ADMIN_ID),
    )

    r = await client.post(
        f"/api/v1/admin/content/review/{vid}/approve",
        json={},
        headers=_hdrs(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_no_warnings_no_ack_required(client):
    """POST approve returns 200 immediately when alex_warnings_count == 0."""
    await _ensure_admin(client)
    vid, _, _ = await _insert_version(client, warnings_count=0)

    r = await client.post(
        f"/api/v1/admin/content/review/{vid}/approve",
        json={},
        headers=_hdrs(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
