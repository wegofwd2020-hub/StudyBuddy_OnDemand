"""
backend/tests/test_admin_demo_teacher_accounts.py

Tests for admin demo teacher account management endpoints:
  GET  /admin/demo-teacher-accounts
  POST /admin/demo-teacher-accounts/{account_id}/extend
  POST /admin/demo-teacher-accounts/{account_id}/revoke
  POST /admin/demo-teacher-requests/{request_id}/resend
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token


# ── Shared helpers ────────────────────────────────────────────────────────────


@contextmanager
def _patch_teacher_celery():
    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            return_value=None,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield


@contextmanager
def _capture_teacher_verification_token():
    captured: list[str] = []

    def _delay(email: str, token: str) -> None:
        captured.append(token)

    with (
        patch(
            "src.demo.teacher_router.send_demo_teacher_verification_email_task.delay",
            side_effect=_delay,
        ),
        patch(
            "src.demo.teacher_router.send_demo_teacher_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield lambda: captured[-1] if captured else None


async def _create_verified_demo_teacher(client: AsyncClient, email: str) -> None:
    """Full request → verify flow for a demo teacher."""
    with _capture_teacher_verification_token() as get_token:
        r = await client.post("/api/v1/demo/teacher/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_teacher_celery():
        rv = await client.get(f"/api/v1/demo/teacher/verify/{token}")
    assert rv.status_code == 200


# ── GET /admin/demo-teacher-accounts ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_requires_admin(client: AsyncClient):
    """No JWT returns 401 or 403."""
    r = await client.get("/api/v1/admin/demo-teacher-accounts")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_requires_correct_role(client: AsyncClient):
    """Tester role (not super_admin/product_admin) returns 403."""
    token = make_admin_token(role="tester")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_empty(client: AsyncClient):
    """super_admin can call the list endpoint; returns valid pagination shape."""
    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_product_admin_allowed(client: AsyncClient):
    """product_admin also has access."""
    token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_contains_request(client: AsyncClient):
    """A submitted demo teacher request appears in the list."""
    email = "teacher-list-appears@example.com"
    with _patch_teacher_celery():
        await client.post("/api/v1/demo/teacher/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    emails = [item["email"] for item in r.json()["items"]]
    assert email in emails


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_email_filter(client: AsyncClient):
    """Email filter narrows results to matching emails."""
    email = "teacher-filter-uniqueabc@example.com"
    with _patch_teacher_celery():
        await client.post("/api/v1/demo/teacher/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": "teacher-filter-uniqueabc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "teacher-filter-uniqueabc" in item["email"]


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_status_filter(client: AsyncClient):
    """Status filter 'pending' returns only pending requests."""
    email = "teacher-status-filter@example.com"
    with _patch_teacher_celery():
        await client.post("/api/v1/demo/teacher/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["request_status"] == "pending"


@pytest.mark.asyncio
async def test_list_demo_teacher_accounts_pagination(client: AsyncClient):
    """page_size parameter is respected."""
    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"page": 1, "page_size": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ── POST /admin/demo-teacher-accounts/{account_id}/extend ────────────────────


@pytest.mark.asyncio
async def test_extend_demo_teacher_account_success(client: AsyncClient):
    """Admin can extend an active demo teacher account."""
    email = "teacher-extend-ok@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_r.json()["items"]
    assert items
    account_id = items[0]["account_id"]
    assert account_id is not None

    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/extend",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "hour" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_extend_demo_teacher_account_not_found(client: AsyncClient):
    """Extending a non-existent account returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{fake_id}/extend",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_extend_demo_teacher_account_already_revoked(client: AsyncClient):
    """Extending a revoked account returns 409."""
    email = "teacher-extend-revoked@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    # Revoke first
    await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )

    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/extend",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_extend_demo_teacher_account_invalid_hours(client: AsyncClient):
    """hours outside [1, 168] returns 422."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{fake_id}/extend",
        json={"hours": 200},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── POST /admin/demo-teacher-accounts/{account_id}/revoke ────────────────────


@pytest.mark.asyncio
async def test_revoke_demo_teacher_account_success(client: AsyncClient):
    """Admin can revoke an active demo teacher account."""
    email = "teacher-revoke-ok@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "revoked" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_revoke_demo_teacher_account_not_found(client: AsyncClient):
    """Revoking a non-existent account returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{fake_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_revoke_demo_teacher_account_already_revoked(client: AsyncClient):
    """Revoking an already-revoked account returns 409."""
    email = "teacher-revoke-twice@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_revoke_demo_teacher_shows_revoked_at_in_list(client: AsyncClient):
    """After revocation the list reflects revoked_at is set."""
    email = "teacher-revoke-check@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    await client.post(
        f"/api/v1/admin/demo-teacher-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )

    list_r2 = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    item = list_r2.json()["items"][0]
    assert item["revoked_at"] is not None


# ── POST /admin/demo-teacher-requests/{request_id}/resend ────────────────────


@pytest.mark.asyncio
async def test_resend_demo_teacher_verification_success(client: AsyncClient):
    """Admin can resend verification for a pending teacher request."""
    email = "teacher-admin-resend@example.com"
    with _patch_teacher_celery():
        await client.post("/api/v1/demo/teacher/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_r.json()["items"]
    assert items
    request_id = items[0]["request_id"]

    with patch(
        "src.auth.tasks.send_demo_teacher_verification_email_task.delay",
        return_value=None,
    ):
        r = await client.post(
            f"/api/v1/admin/demo-teacher-requests/{request_id}/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert "resent" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_resend_demo_teacher_verification_not_found(client: AsyncClient):
    """Resend for unknown request_id returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-teacher-requests/{fake_id}/resend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_resend_demo_teacher_verification_non_pending(client: AsyncClient):
    """Resend for a verified (non-pending) request returns 409."""
    email = "teacher-admin-resend-verified@example.com"
    await _create_verified_demo_teacher(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-teacher-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    request_id = list_r.json()["items"][0]["request_id"]

    r = await client.post(
        f"/api/v1/admin/demo-teacher-requests/{request_id}/resend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
