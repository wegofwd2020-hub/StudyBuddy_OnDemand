"""
tests/test_admin_retention.py

Integration tests for the admin platform-wide retention monitor.

Endpoints under test:
  GET  /api/v1/admin/retention
  POST /api/v1/admin/schools/{school_id}/curriculum/versions/{curriculum_id}/action

All tests use signed admin JWTs (make_admin_token). School curricula are seeded
directly via the app pool with RLS bypassed (app.current_school_id = 'bypass').
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from main import app
from tests.helpers.token_factory import make_admin_token, make_teacher_token


# ── Test helpers ──────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient, *, school_name: str | None = None) -> dict:
    """Register a school and return {school_id, teacher_id, token}."""
    name = school_name or f"Retention Admin Test School {uuid.uuid4().hex[:6]}"
    r = await client.post("/api/v1/schools/register", json={
        "school_name": name,
        "contact_email": f"admin-ret-{uuid.uuid4().hex[:8]}@example.com",
        "country": "US",
        "password": "SecureTestPwd1!",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    teacher_token = make_teacher_token(
        teacher_id=body["teacher_id"],
        school_id=body["school_id"],
        role="school_admin",
    )
    return {**body, "teacher_token": teacher_token}


async def _seed_curriculum(
    school_id: str,
    grade: int = 8,
    year: int = 2026,
    *,
    retention_status: str = "active",
    expires_at: datetime | None = None,
    grace_until: datetime | None = None,
) -> str:
    """Insert a curricula row directly via the app pool (RLS bypassed)."""
    curriculum_id = str(uuid.uuid4())
    exp = expires_at or (datetime.now(UTC) + timedelta(days=365))
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, grade, year, name, is_default, source_type,
                 school_id, status, owner_type, owner_id, retention_status,
                 expires_at, grace_until)
            VALUES ($1, $2, $3, $4, false, 'school', $5::uuid, 'active',
                    'school', $5::uuid, $6, $7, $8)
            ON CONFLICT (curriculum_id) DO UPDATE
                SET retention_status = EXCLUDED.retention_status,
                    expires_at       = EXCLUDED.expires_at,
                    grace_until      = EXCLUDED.grace_until
            """,
            curriculum_id, grade, year, f"Grade {grade} Curriculum ({year})",
            school_id, retention_status, exp, grace_until,
        )
    return curriculum_id


async def _pool_fetchrow(query: str, *args):
    """Run a SELECT with RLS bypass and return the first row."""
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        return await conn.fetchrow(query, *args)


# ── GET /admin/retention ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_retention_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/admin/retention")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_retention_rejects_developer(client: AsyncClient):
    token = make_admin_token(role="developer")
    r = await client.get(
        "/api/v1/admin/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_retention_rejects_tester(client: AsyncClient):
    token = make_admin_token(role="tester")
    r = await client.get(
        "/api/v1/admin/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_retention_product_admin_allowed(client: AsyncClient):
    token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    assert "curricula" in body


@pytest.mark.asyncio
async def test_admin_retention_returns_all_schools(client: AsyncClient):
    """Platform view includes curricula from multiple schools."""
    reg1 = await _register_school(client, school_name="School Alpha")
    reg2 = await _register_school(client, school_name="School Beta")
    now = datetime.now(UTC)

    cid1 = await _seed_curriculum(reg1["school_id"], grade=7, retention_status="active",
                                   expires_at=now + timedelta(days=100))
    cid2 = await _seed_curriculum(reg2["school_id"], grade=9, retention_status="unavailable",
                                   expires_at=now - timedelta(days=10),
                                   grace_until=now + timedelta(days=170))

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    curriculum_ids = [c["curriculum_id"] for c in body["curricula"]]
    assert cid1 in curriculum_ids
    assert cid2 in curriculum_ids


@pytest.mark.asyncio
async def test_admin_retention_summary_counts(client: AsyncClient):
    """Summary counts reflect seeded statuses across schools."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)

    await _seed_curriculum(sid, grade=5, retention_status="active",
                            expires_at=now + timedelta(days=200))
    await _seed_curriculum(sid, grade=6, retention_status="unavailable",
                            expires_at=now - timedelta(days=5),
                            grace_until=now + timedelta(days=175))
    await _seed_curriculum(sid, grade=7, retention_status="purged",
                            expires_at=now - timedelta(days=200))

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        params={"school_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    summary = r.json()["summary"]
    assert summary["active"] >= 1
    assert summary["unavailable"] >= 1
    assert summary["purged"] >= 1


@pytest.mark.asyncio
async def test_admin_retention_expiring_soon_counted(client: AsyncClient):
    """expiring_soon counts active curricula within the threshold."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)

    await _seed_curriculum(sid, grade=8, retention_status="active",
                            expires_at=now + timedelta(days=10))

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        params={"school_id": sid, "expiring_days": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["summary"]["expiring_soon"] >= 1


@pytest.mark.asyncio
async def test_admin_retention_status_filter(client: AsyncClient):
    """status filter restricts results to matching rows only."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)

    await _seed_curriculum(sid, grade=5, retention_status="active",
                            expires_at=now + timedelta(days=200))
    await _seed_curriculum(sid, grade=6, retention_status="purged",
                            expires_at=now - timedelta(days=200))

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        params={"school_id": sid, "status": "purged"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    for c in r.json()["curricula"]:
        assert c["retention_status"] == "purged"


@pytest.mark.asyncio
async def test_admin_retention_grade_filter(client: AsyncClient):
    """grade filter restricts to specific grade."""
    reg = await _register_school(client)
    sid = reg["school_id"]

    await _seed_curriculum(sid, grade=5)
    await _seed_curriculum(sid, grade=10)

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        params={"school_id": sid, "grade": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    for c in r.json()["curricula"]:
        assert c["grade"] == 5


@pytest.mark.asyncio
async def test_admin_retention_urgency_sort(client: AsyncClient):
    """Unavailable (soonest grace) should appear before active in results."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)

    await _seed_curriculum(sid, grade=8, retention_status="active",
                            expires_at=now + timedelta(days=300))
    await _seed_curriculum(sid, grade=9, retention_status="unavailable",
                            expires_at=now - timedelta(days=10),
                            grace_until=now + timedelta(days=5))

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/retention",
        params={"school_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    items = r.json()["curricula"]
    # Filter to just our two seeded items
    ours = [c for c in items if c["school_id"] == sid]
    statuses = [c["retention_status"] for c in ours]
    assert statuses.index("unavailable") < statuses.index("active")


# ── POST .../action — renew ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_action_renew_active(client: AsyncClient):
    """Admin can renew an active curriculum; expiry is extended by 1 year."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)
    original_expiry = now + timedelta(days=30)
    cid = await _seed_curriculum(sid, grade=8, retention_status="active",
                                  expires_at=original_expiry)

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "renew", "reason": "School support ticket #999"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["new_retention_status"] == "active"
    # New expiry should be roughly 1 year beyond original
    new_exp = datetime.fromisoformat(body["new_expires_at"])
    assert new_exp > original_expiry + timedelta(days=360)


@pytest.mark.asyncio
async def test_admin_action_renew_unavailable(client: AsyncClient):
    """Admin can renew a curriculum that is in grace period (unavailable)."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)
    cid = await _seed_curriculum(sid, grade=9, retention_status="unavailable",
                                  expires_at=now - timedelta(days=10),
                                  grace_until=now + timedelta(days=170))

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "renew", "reason": "Admin renewal on behalf of school"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["new_retention_status"] == "active"


@pytest.mark.asyncio
async def test_admin_action_renew_purged_rejected(client: AsyncClient):
    """Renewing a purged curriculum returns 409."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)
    cid = await _seed_curriculum(sid, grade=10, retention_status="purged",
                                  expires_at=now - timedelta(days=200))

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "renew", "reason": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "already_purged"


# ── POST .../action — force_expire ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_action_force_expire(client: AsyncClient):
    """force_expire transitions active → unavailable with 180-day grace."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=11, retention_status="active")

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "force_expire", "reason": "School requested removal of access"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_retention_status"] == "unavailable"
    assert body["new_grace_until"] is not None
    grace = datetime.fromisoformat(body["new_grace_until"])
    assert grace > datetime.now(UTC) + timedelta(days=170)


@pytest.mark.asyncio
async def test_admin_action_force_expire_unavailable_rejected(client: AsyncClient):
    """force_expire on an already-unavailable curriculum returns 409."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    now = datetime.now(UTC)
    cid = await _seed_curriculum(sid, grade=12, retention_status="unavailable",
                                  grace_until=now + timedelta(days=100))

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "force_expire", "reason": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "not_active"


# ── POST .../action — force_delete ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_action_force_delete(client: AsyncClient):
    """force_delete removes the curriculum row regardless of grade assignment."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=8, retention_status="active")

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "force_delete", "reason": "School decommissioned"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["action"] == "force_delete"

    # Curriculum row must be gone
    row = await _pool_fetchrow(
        "SELECT curriculum_id FROM curricula WHERE curriculum_id = $1", cid
    )
    assert row is None


@pytest.mark.asyncio
async def test_admin_action_force_delete_bypasses_grade_assignment(client: AsyncClient):
    """force_delete removes grade_curriculum_assignments before deleting the row."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=8, retention_status="active")

    # Assign this curriculum to grade 8 (assigned_by must be a teacher_id)
    teacher_id = reg["teacher_id"]
    async with app.state.pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO grade_curriculum_assignments (school_id, grade, curriculum_id, assigned_by)
            VALUES ($1::uuid, $2, $3, $4::uuid)
            ON CONFLICT (school_id, grade) DO UPDATE
                SET curriculum_id = EXCLUDED.curriculum_id
            """,
            sid, 8, cid, teacher_id,
        )

    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "force_delete", "reason": "Admin override — school decommissioned"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should succeed despite being assigned (admin bypass)
    assert r.status_code == 200
    assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_force_delete_removes_content_files(client: AsyncClient):
    """
    force_delete calls StorageBackend.delete_tree for the curriculum's content
    directory in addition to removing the DB rows.
    """
    from unittest.mock import AsyncMock

    from main import app as _app

    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=9, retention_status="active")

    # Patch delete_tree on the live storage instance so we can assert it's called.
    original_delete_tree = _app.state.storage.delete_tree
    mock_delete = AsyncMock(return_value=None)
    _app.state.storage.delete_tree = mock_delete

    token = make_admin_token(role="super_admin")
    try:
        r = await client.post(
            f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
            json={"action": "force_delete", "reason": "Content files must be removed"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        _app.state.storage.delete_tree = original_delete_tree

    assert r.status_code == 200
    assert r.json()["success"] is True

    # delete_tree must have been called with the curriculum's content path.
    mock_delete.assert_called_once_with(f"curricula/{cid}")


@pytest.mark.asyncio
async def test_admin_force_delete_succeeds_even_if_file_deletion_fails(client: AsyncClient):
    """
    If storage.delete_tree raises (e.g. S3 permission error), force_delete still
    returns 200 — the DB row is gone, which is the correctness-critical outcome.
    File cleanup can be retried manually.
    """
    from unittest.mock import AsyncMock, patch

    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=10, retention_status="unavailable")

    token = make_admin_token(role="super_admin")

    with patch(
        "src.admin.retention_router.get_storage",
        return_value=lambda: None,  # not used — we patch the StorageBackend directly
    ):
        pass  # approach: patch delete_tree on the actual app.state.storage instance

    from main import app as _app
    original_delete_tree = _app.state.storage.delete_tree
    _app.state.storage.delete_tree = AsyncMock(side_effect=Exception("S3 permission denied"))

    try:
        r = await client.post(
            f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
            json={"action": "force_delete", "reason": "Resilience test"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        _app.state.storage.delete_tree = original_delete_tree

    # Action must still succeed — DB is the source of truth.
    assert r.status_code == 200
    assert r.json()["success"] is True

    # Curriculum row is gone despite the storage error.
    row = await _pool_fetchrow(
        "SELECT curriculum_id FROM curricula WHERE curriculum_id = $1", cid
    )
    assert row is None


# ── Auth guards for action endpoint ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_action_requires_auth(client: AsyncClient):
    r = await client.post(
        "/api/v1/admin/schools/any-school/curriculum/versions/any-cid/action",
        json={"action": "renew", "reason": "Test"},
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_action_rejects_developer(client: AsyncClient):
    token = make_admin_token(role="developer")
    r = await client.post(
        "/api/v1/admin/schools/any-school/curriculum/versions/any-cid/action",
        json={"action": "renew", "reason": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_action_not_found(client: AsyncClient):
    """Unknown curriculum returns 404."""
    reg = await _register_school(client)
    token = make_admin_token(role="super_admin")
    r = await client.post(
        f"/api/v1/admin/schools/{reg['school_id']}/curriculum/versions/nonexistent-cid/action",
        json={"action": "renew", "reason": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_admin_action_audit_log_written(client: AsyncClient):
    """Every action writes an audit_log entry."""
    reg = await _register_school(client)
    sid = reg["school_id"]
    cid = await _seed_curriculum(sid, grade=6, retention_status="active")

    token = make_admin_token(role="super_admin")
    await client.post(
        f"/api/v1/admin/schools/{sid}/curriculum/versions/{cid}/action",
        json={"action": "force_expire", "reason": "Audit test reason"},
        headers={"Authorization": f"Bearer {token}"},
    )

    row = await _pool_fetchrow(
        "SELECT event_type, actor_type, target_id FROM audit_log WHERE target_id = $1 ORDER BY timestamp DESC LIMIT 1",
        cid,
    )
    assert row is not None
    assert row["event_type"] == "admin_curriculum_force_expire"
    assert row["actor_type"] == "admin"
    assert str(row["target_id"]) == cid
