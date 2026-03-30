"""
backend/tests/test_admin_demo_accounts.py

Tests for issue #35 — Admin demo account management endpoints:
  GET  /admin/demo-accounts
  POST /admin/demo-accounts/{account_id}/extend
  POST /admin/demo-accounts/{account_id}/revoke
  POST /admin/demo-requests/{request_id}/resend

Strategy:
  - RBAC tests use token_factory helpers directly.
  - State setup uses sequential API calls through the demo endpoints (same
    isolation strategy as test_demo_endpoints.py).
  - Celery tasks are always patched — no live workers needed.
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
def _patch_celery():
    with (
        patch("src.demo.router.send_demo_verification_email_task.delay", return_value=None),
        patch("src.demo.router.send_demo_credentials_email_task.delay", return_value=None),
    ):
        yield


@contextmanager
def _capture_verification_token():
    captured: list[str] = []

    def _delay(email: str, token: str) -> None:
        captured.append(token)

    with (
        patch("src.demo.router.send_demo_verification_email_task.delay", side_effect=_delay),
        patch("src.demo.router.send_demo_credentials_email_task.delay", return_value=None),
    ):
        yield lambda: captured[-1] if captured else None


async def _create_verified_demo(client: AsyncClient, email: str) -> str:
    """Full request → verify flow; returns demo_account_id from the list endpoint."""
    with _capture_verification_token() as get_token:
        r = await client.post("/api/v1/demo/request", json={"email": email})
    assert r.status_code == 200
    token = get_token()
    assert token is not None

    with _patch_celery():
        rv = await client.get(f"/api/v1/demo/verify/{token}")
    assert rv.status_code == 200
    return token  # caller fetches account_id via list endpoint


# ── GET /admin/demo-accounts ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_demo_accounts_requires_admin(client: AsyncClient):
    """Request without admin JWT returns 401/403."""
    r = await client.get("/api/v1/admin/demo-accounts")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_demo_accounts_requires_demo_manage_role(client: AsyncClient):
    """Tester role (not super_admin/product_admin) is rejected with 403."""
    token = make_admin_token(role="tester")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


@pytest.mark.asyncio
async def test_list_demo_accounts_empty(client: AsyncClient):
    """Super-admin can call the list endpoint; returns valid pagination shape."""
    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_demo_accounts_product_admin_allowed(client: AsyncClient):
    """product_admin role also has demo:manage access."""
    token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_demo_accounts_contains_request(client: AsyncClient):
    """A submitted demo request appears in the list."""
    email = "list-test@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    emails = [item["email"] for item in r.json()["items"]]
    assert email in emails


@pytest.mark.asyncio
async def test_list_demo_accounts_email_filter(client: AsyncClient):
    """Email filter narrows results to matching emails only."""
    email = "filter-unique-xyz@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": "filter-unique-xyz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "filter-unique-xyz" in item["email"]


@pytest.mark.asyncio
async def test_list_demo_accounts_status_filter_pending(client: AsyncClient):
    """Status filter 'pending' returns only pending requests."""
    email = "status-filter-pending@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["request_status"] == "pending"


@pytest.mark.asyncio
async def test_list_demo_accounts_pagination(client: AsyncClient):
    """page_size parameter is respected."""
    token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"page": 1, "page_size": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ── POST /admin/demo-accounts/{account_id}/extend ────────────────────────────


@pytest.mark.asyncio
async def test_extend_demo_account_success(client: AsyncClient):
    """Admin can extend an active demo account's TTL."""
    email = "extend-ok@example.com"
    await _create_verified_demo(client, email)

    # Fetch account_id from the list
    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_r.json()["items"]
    assert items, "Account should appear in list"
    account_id = items[0]["account_id"]
    assert account_id is not None

    r = await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/extend",
        json={"hours": 48},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["account_id"] == account_id
    assert "expires_at" in data
    assert "extended_at" in data


@pytest.mark.asyncio
async def test_extend_demo_account_not_found(client: AsyncClient):
    """Extending a non-existent account returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-accounts/{fake_id}/extend",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_extend_demo_account_already_revoked(client: AsyncClient):
    """Extending a revoked account returns 409."""
    email = "extend-revoked@example.com"
    await _create_verified_demo(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    # Revoke first
    await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Now try to extend
    r = await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/extend",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "already_revoked"


@pytest.mark.asyncio
async def test_extend_demo_account_invalid_hours(client: AsyncClient):
    """hours outside [1, 168] is rejected with 422."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-accounts/{fake_id}/extend",
        json={"hours": 200},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ── POST /admin/demo-accounts/{account_id}/revoke ────────────────────────────


@pytest.mark.asyncio
async def test_revoke_demo_account_success(client: AsyncClient):
    """Admin can revoke an active demo account."""
    email = "revoke-ok@example.com"
    await _create_verified_demo(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    r = await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == email
    assert "revoked" in data["message"].lower()


@pytest.mark.asyncio
async def test_revoke_demo_account_not_found(client: AsyncClient):
    """Revoking a non-existent account returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-accounts/{fake_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_revoke_demo_account_already_revoked(client: AsyncClient):
    """Revoking an already-revoked account returns 409."""
    email = "revoke-twice@example.com"
    await _create_verified_demo(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "already_revoked"


@pytest.mark.asyncio
async def test_revoke_demo_account_marks_student_deleted(client: AsyncClient):
    """After revoke, the account shows revoked_at in the list."""
    email = "revoke-student@example.com"
    await _create_verified_demo(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = list_r.json()["items"][0]["account_id"]

    await client.post(
        f"/api/v1/admin/demo-accounts/{account_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check list reflects revocation
    list_r2 = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    item = list_r2.json()["items"][0]
    assert item["revoked_at"] is not None


# ── POST /admin/demo-requests/{request_id}/resend ────────────────────────────


@pytest.mark.asyncio
async def test_admin_resend_verification_success(client: AsyncClient):
    """Admin can resend verification for a pending request."""
    email = "admin-resend-ok@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_r.json()["items"]
    assert items
    request_id = str(items[0]["request_id"])

    with patch("src.admin.demo_accounts.send_demo_verification_email_task.delay", return_value=None):
        r = await client.post(
            f"/api/v1/admin/demo-requests/{request_id}/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.json()["email"] == email


@pytest.mark.asyncio
async def test_admin_resend_verification_not_found(client: AsyncClient):
    """Resend for unknown request_id returns 404."""
    token = make_admin_token(role="super_admin")
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/demo-requests/{fake_id}/resend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_admin_resend_verification_non_pending(client: AsyncClient):
    """Resend for a verified request returns 409."""
    email = "admin-resend-verified@example.com"
    await _create_verified_demo(client, email)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    request_id = str(list_r.json()["items"][0]["request_id"])

    r = await client.post(
        f"/api/v1/admin/demo-requests/{request_id}/resend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "not_pending"


@pytest.mark.asyncio
async def test_admin_resend_fires_celery_task(client: AsyncClient):
    """Resend dispatches the verification email Celery task."""
    email = "admin-resend-celery@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    request_id = str(list_r.json()["items"][0]["request_id"])

    fired: list[tuple] = []

    def _capture(e, t):
        fired.append((e, t))

    with patch("src.admin.demo_accounts.send_demo_verification_email_task.delay", side_effect=_capture):
        r = await client.post(
            f"/api/v1/admin/demo-requests/{request_id}/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert fired, "Celery task was not dispatched"
    assert fired[0][0] == email


@pytest.mark.asyncio
async def test_admin_resend_no_cooldown_enforcement(client: AsyncClient, fake_redis):
    """Admin resend bypasses the user-facing cooldown (no Redis check)."""
    email = "admin-no-cooldown@example.com"
    with _patch_celery():
        await client.post("/api/v1/demo/request", json={"email": email})

    # Simulate an active user-side cooldown key
    await fake_redis.set(f"demo_resend:{email}", "1", ex=300)

    token = make_admin_token(role="super_admin")
    list_r = await client.get(
        "/api/v1/admin/demo-accounts",
        params={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    request_id = str(list_r.json()["items"][0]["request_id"])

    with patch("src.admin.demo_accounts.send_demo_verification_email_task.delay", return_value=None):
        r = await client.post(
            f"/api/v1/admin/demo-requests/{request_id}/resend",
            headers={"Authorization": f"Bearer {token}"},
        )
    # Admin endpoint must NOT be blocked by the user-side cooldown
    assert r.status_code == 200
