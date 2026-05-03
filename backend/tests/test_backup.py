"""
backend/tests/test_backup.py

Epic 15 — Curriculum Backup & Restore API tests.

Coverage:
  School endpoints (school_admin, own school):
    GET    /schools/{id}/backups                               — list backups
    POST   /schools/{id}/restore-requests                     — submit request
    GET    /schools/{id}/restore-requests                     — list requests
    GET    /schools/{id}/restore-requests/{req_id}            — get single request
    PATCH  /schools/{id}/restore-requests/{req_id}/cancel     — school cancel
    PATCH  /schools/{id}/restore-requests/{req_id}/confirm    — confirm override

  Admin endpoints (super_admin):
    GET    /admin/backups                                      — list all
    GET    /admin/backups/{id}                                 — get single
    GET    /admin/restore-requests                             — list all
    PATCH  /admin/restore-requests/{id}/acknowledge           — acknowledge
    PATCH  /admin/restore-requests/{id}/cancel                — admin cancel
    GET    /admin/backup-schedules                            — list schedules
    PUT    /admin/backup-schedules/{school_id}                — update schedule
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token, make_teacher_token

# ── Fixed IDs ─────────────────────────────────────────────────────────────────

_ADMIN_ID = "00000000-0000-0000-0000-000000000077"
_PW = "SecureTestPwd12!"


# ── Header helpers ────────────────────────────────────────────────────────────


def _admin_hdr(role: str = "super_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=_ADMIN_ID, role=role)}"}


def _school_hdr(school_id: str, teacher_id: str, role: str = "school_admin") -> dict:
    tok = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role=role)
    return {"Authorization": f"Bearer {tok}"}


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _seed_admin(client: AsyncClient) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, role, password_hash)
        VALUES ($1, 'backup-admin@test.invalid', 'super_admin', 'x')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(_ADMIN_ID),
    )


async def _register_school(client: AsyncClient, suffix: str) -> tuple[str, str]:
    """Register a school; return (school_id, teacher_id)."""
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Backup Test School {suffix}",
            "contact_email": f"backup-{suffix}@backup.example.com",
            "country": "CA",
            "password": _PW,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["school_id"], body["teacher_id"]


async def _seed_backup(
    client: AsyncClient,
    school_id: str,
    status: str = "completed",
) -> str:
    """Insert a curriculum_backups row, bypassing RLS; return the new backup_id."""
    backup_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO curriculum_backups
                (id, school_id, label, scope_type, status)
            VALUES ($1, $2, 'Test backup', 'full', $3)
            """,
            uuid.UUID(backup_id),
            uuid.UUID(school_id),
            status,
        )
    return backup_id


async def _seed_restore_request(
    client: AsyncClient,
    school_id: str,
    backup_id: str,
    status: str = "submitted",
) -> str:
    """Insert a backup_restore_requests row, bypassing RLS; return the new request_id."""
    request_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        await conn.execute(
            """
            INSERT INTO backup_restore_requests
                (id, school_id, backup_id, scope_type, status)
            VALUES ($1, $2, $3, 'full', $4)
            """,
            uuid.UUID(request_id),
            uuid.UUID(school_id),
            uuid.UUID(backup_id),
            status,
        )
    return request_id


# ── School: list backups ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_school_list_backups_empty(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "bk-01")
    r = await client.get(
        f"/api/v1/schools/{school_id}/backups",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 0
    assert body["backups"] == []


@pytest.mark.asyncio
async def test_school_list_backups_returns_own_backup(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "bk-02")
    await _seed_backup(client, school_id, status="completed")
    r = await client.get(
        f"/api/v1/schools/{school_id}/backups",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["backups"][0]["status"] == "completed"
    assert body["backups"][0]["school_id"] == school_id


@pytest.mark.asyncio
async def test_school_list_backups_wrong_school_forbidden(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "bk-03")
    other_school_id, _ = await _register_school(client, "bk-03b")
    # Token scoped to other_school — must not see school_id's backups
    r = await client.get(
        f"/api/v1/schools/{school_id}/backups",
        headers=_school_hdr(other_school_id, teacher_id),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_list_backups_teacher_role_forbidden(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "bk-04")
    r = await client.get(
        f"/api/v1/schools/{school_id}/backups",
        headers=_school_hdr(school_id, teacher_id, role="teacher"),
    )
    assert r.status_code == 403


# ── School: submit restore request ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_school_submit_restore_request_ok(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "rr-01")
    backup_id = await _seed_backup(client, school_id, status="completed")
    r = await client.post(
        f"/api/v1/schools/{school_id}/restore-requests",
        json={
            "backup_id": backup_id,
            "scope_type": "full",
            "notes": "Test restore",
            "side_by_side": False,
        },
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "submitted"
    assert body["backup_id"] == backup_id
    assert body["scope_type"] == "full"


@pytest.mark.asyncio
async def test_school_submit_restore_request_backup_not_found(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "rr-02")
    missing_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/schools/{school_id}/restore-requests",
        json={"backup_id": missing_id, "scope_type": "full"},
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_school_submit_restore_request_non_completed_backup_rejected(
    client: AsyncClient,
):
    school_id, teacher_id = await _register_school(client, "rr-03")
    backup_id = await _seed_backup(client, school_id, status="pending")
    r = await client.post(
        f"/api/v1/schools/{school_id}/restore-requests",
        json={"backup_id": backup_id, "scope_type": "full"},
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_school_submit_restore_deduplicates(client: AsyncClient):
    """Second submit for the same school+backup+scope cancels the prior open request."""
    school_id, teacher_id = await _register_school(client, "rr-04")
    backup_id = await _seed_backup(client, school_id, status="completed")
    hdr = _school_hdr(school_id, teacher_id)
    payload = {"backup_id": backup_id, "scope_type": "full"}

    r1 = await client.post(
        f"/api/v1/schools/{school_id}/restore-requests", json=payload, headers=hdr
    )
    assert r1.status_code == 200
    req1_id = r1.json()["id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/restore-requests", json=payload, headers=hdr
    )
    assert r2.status_code == 200
    req2_id = r2.json()["id"]
    assert req2_id != req1_id

    # First request must now be cancelled
    r3 = await client.get(
        f"/api/v1/schools/{school_id}/restore-requests/{req1_id}", headers=hdr
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "cancelled"


# ── School: list / get / cancel restore requests ─────────────────────────────


@pytest.mark.asyncio
async def test_school_list_restore_requests(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "rr-10")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id)
    r = await client.get(
        f"/api/v1/schools/{school_id}/restore-requests",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    ids = [req["id"] for req in body["requests"]]
    assert req_id in ids


@pytest.mark.asyncio
async def test_school_get_restore_request(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "rr-11")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="submitted")
    r = await client.get(
        f"/api/v1/schools/{school_id}/restore-requests/{req_id}",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == req_id
    assert r.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_school_cancel_restore_request(client: AsyncClient):
    school_id, teacher_id = await _register_school(client, "rr-12")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="submitted")
    r = await client.patch(
        f"/api/v1/schools/{school_id}/restore-requests/{req_id}/cancel",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_school_cancel_restore_request_wrong_status(client: AsyncClient):
    """School cannot cancel a request that is already acknowledged."""
    school_id, teacher_id = await _register_school(client, "rr-13")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="acknowledged")
    r = await client.patch(
        f"/api/v1/schools/{school_id}/restore-requests/{req_id}/cancel",
        headers=_school_hdr(school_id, teacher_id),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_school_confirm_restore_override(client: AsyncClient):
    """Confirming an awaiting_school_confirm request advances it to in_progress."""
    school_id, teacher_id = await _register_school(client, "rr-14")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(
        client, school_id, backup_id, status="awaiting_school_confirm"
    )
    with patch("src.backup.tasks.execute_restore_task.delay", return_value=None):
        r = await client.patch(
            f"/api/v1/schools/{school_id}/restore-requests/{req_id}/confirm",
            json={"side_by_side": True},
            headers=_school_hdr(school_id, teacher_id),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["side_by_side"] is True


@pytest.mark.asyncio
async def test_school_confirm_wrong_status(client: AsyncClient):
    """Confirming a submitted (not awaiting) request returns 400."""
    school_id, teacher_id = await _register_school(client, "rr-15")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="submitted")
    with patch("src.backup.tasks.execute_restore_task.delay", return_value=None):
        r = await client.patch(
            f"/api/v1/schools/{school_id}/restore-requests/{req_id}/confirm",
            json={"side_by_side": False},
            headers=_school_hdr(school_id, teacher_id),
        )
    assert r.status_code == 400


# ── Admin: backups ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_all_backups(client: AsyncClient):
    await _seed_admin(client)
    r = await client.get("/api/v1/admin/backups", headers=_admin_hdr())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "backups" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_admin_list_all_backups_forbidden_for_product_admin(client: AsyncClient):
    await _seed_admin(client)
    r = await client.get("/api/v1/admin/backups", headers=_admin_hdr(role="product_admin"))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_get_backup_found(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "adm-01")
    backup_id = await _seed_backup(client, school_id, status="completed")
    r = await client.get(f"/api/v1/admin/backups/{backup_id}", headers=_admin_hdr())
    assert r.status_code == 200, r.text
    assert r.json()["id"] == backup_id
    assert r.json()["school_id"] == school_id


@pytest.mark.asyncio
async def test_admin_get_backup_not_found(client: AsyncClient):
    await _seed_admin(client)
    r = await client.get(
        f"/api/v1/admin/backups/{uuid.uuid4()}", headers=_admin_hdr()
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_list_school_backups(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "adm-02")
    await _seed_backup(client, school_id, status="running")
    r = await client.get(
        f"/api/v1/admin/schools/{school_id}/backups", headers=_admin_hdr()
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert all(b["school_id"] == school_id for b in body["backups"])


# ── Admin: restore requests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_restore_requests(client: AsyncClient):
    await _seed_admin(client)
    r = await client.get("/api/v1/admin/restore-requests", headers=_admin_hdr())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "requests" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_admin_acknowledge_restore_request(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "adm-10")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="submitted")
    with patch("src.backup.tasks.dry_run_restore_task.delay", return_value=None):
        r = await client.patch(
            f"/api/v1/admin/restore-requests/{req_id}/acknowledge",
            headers=_admin_hdr(),
        )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_admin_acknowledge_wrong_status(client: AsyncClient):
    """Acknowledging an already-acknowledged request returns 400."""
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "adm-11")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(
        client, school_id, backup_id, status="acknowledged"
    )
    with patch("src.backup.tasks.dry_run_restore_task.delay", return_value=None):
        r = await client.patch(
            f"/api/v1/admin/restore-requests/{req_id}/acknowledge",
            headers=_admin_hdr(),
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_cancel_restore_request(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "adm-12")
    backup_id = await _seed_backup(client, school_id)
    req_id = await _seed_restore_request(client, school_id, backup_id, status="submitted")
    r = await client.patch(
        f"/api/v1/admin/restore-requests/{req_id}/cancel",
        headers=_admin_hdr(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_admin_cancel_restore_request_not_found(client: AsyncClient):
    await _seed_admin(client)
    r = await client.patch(
        f"/api/v1/admin/restore-requests/{uuid.uuid4()}/cancel",
        headers=_admin_hdr(),
    )
    assert r.status_code == 404


# ── Admin: backup schedules ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_backup_schedules(client: AsyncClient):
    await _seed_admin(client)
    await _register_school(client, "sched-01")
    r = await client.get("/api/v1/admin/backup-schedules", headers=_admin_hdr())
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert all("school_id" in s and "cron" in s for s in items)


@pytest.mark.asyncio
async def test_admin_update_backup_schedule(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "sched-02")
    r = await client.put(
        f"/api/v1/admin/backup-schedules/{school_id}",
        json={"cron": "0 3 * * *"},
        headers=_admin_hdr(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cron"] == "0 3 * * *"
    assert body["school_id"] == school_id


@pytest.mark.asyncio
async def test_admin_backup_schedule_forbidden_non_super_admin(client: AsyncClient):
    await _seed_admin(client)
    school_id, _ = await _register_school(client, "sched-03")
    r = await client.put(
        f"/api/v1/admin/backup-schedules/{school_id}",
        json={"cron": "0 4 * * *"},
        headers=_admin_hdr(role="product_admin"),
    )
    assert r.status_code == 403
