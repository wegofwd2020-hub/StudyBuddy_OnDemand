"""
backend/tests/test_admin_demo_test_runs.py

Tests for admin endpoints managing visitor test-runs:
  GET    /admin/demo/test-runs
  DELETE /admin/demo/test-runs/by-email
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token

_PRODUCT_ADMIN = make_admin_token(role="product_admin")
_SUPER_ADMIN = make_admin_token(role="super_admin")
_DEVELOPER = make_admin_token(role="developer")


@contextmanager
def _patch_test_run_emails():
    captured: dict = {}

    def _capture_token(_email: str, token: str) -> None:
        captured["token"] = token

    with (
        patch(
            "src.demo.test_run_router.send_test_run_verification_email_task.delay",
            side_effect=_capture_token,
        ),
        patch(
            "src.demo.test_run_router.send_test_run_credentials_email_task.delay",
            return_value=None,
        ),
    ):
        yield captured


async def _submit_test_run(client: AsyncClient, name: str, email: str) -> str:
    """Run the full request → verify cycle and return the captured token."""
    with _patch_test_run_emails() as captured:
        r = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": name, "email": email},
        )
        assert r.status_code == 200, r.text
        token = captured["token"]
        rv = await client.get(f"/api/v1/demo/test-run/verify/{token}")
        assert rv.status_code == 200, rv.text
    return token


# ── GET /admin/demo/test-runs ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_test_runs_shows_name_and_original_email(client: AsyncClient):
    await _submit_test_run(client, "Pat Tester", "pat.admin-list@example.com")

    r = await client.get(
        "/api/v1/admin/demo/test-runs",
        headers={"Authorization": f"Bearer {_PRODUCT_ADMIN}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    matching = [item for item in data["items"] if item["email"] == "pat.admin-list@example.com"]
    assert len(matching) == 1
    item = matching[0]
    assert item["name"] == "Pat Tester"
    assert item["student_email"] == "pat.admin-list+student@example.com"
    assert item["teacher_email"] == "pat.admin-list+teacher@example.com"
    # Both sides were verified above, so the per-role expiries are populated.
    assert item["student_expires_at"]
    assert item["teacher_expires_at"]


@pytest.mark.asyncio
async def test_admin_list_test_runs_requires_admin_role(client: AsyncClient):
    """Developer role is rejected — only product_admin / super_admin allowed."""
    r = await client.get(
        "/api/v1/admin/demo/test-runs",
        headers={"Authorization": f"Bearer {_DEVELOPER}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_test_runs_unauthenticated_returns_401(client: AsyncClient):
    r = await client.get("/api/v1/admin/demo/test-runs")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_test_runs_email_filter(client: AsyncClient):
    await _submit_test_run(client, "Visitor A", "filter-a@example.com")
    await _submit_test_run(client, "Visitor B", "filter-b@example.com")

    r = await client.get(
        "/api/v1/admin/demo/test-runs?email=filter-a",
        headers={"Authorization": f"Bearer {_SUPER_ADMIN}"},
    )
    assert r.status_code == 200
    emails = {item["email"] for item in r.json()["items"]}
    assert "filter-a@example.com" in emails
    assert "filter-b@example.com" not in emails


# ── DELETE /admin/demo/test-runs/by-email ─────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_test_run_allows_re_request(client: AsyncClient):
    """
    After deleting a test run, the same email can submit a new test-run
    request — the duplicate-pending / active guards no longer trip.
    """
    email = "purge-and-retry@example.com"

    await _submit_test_run(client, "First Submission", email)

    # Confirm a second request without purge is blocked (409 from "active" guard)
    with _patch_test_run_emails():
        r_blocked = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Second", "email": email},
        )
    assert r_blocked.status_code == 409

    # Purge via admin endpoint
    r_purge = await client.request(
        "DELETE",
        f"/api/v1/admin/demo/test-runs/by-email?email={email}",
        headers={"Authorization": f"Bearer {_SUPER_ADMIN}"},
    )
    assert r_purge.status_code == 200, r_purge.text
    purge_data = r_purge.json()
    assert purge_data["student_requests_deleted"] == 1
    assert purge_data["teacher_requests_deleted"] == 1
    assert purge_data["students_deleted"] == 1
    assert purge_data["teachers_deleted"] == 1

    # Re-request now succeeds
    with _patch_test_run_emails():
        r_again = await client.post(
            "/api/v1/demo/test-run/request",
            json={"name": "Second", "email": email},
        )
    assert r_again.status_code == 200, r_again.text


@pytest.mark.asyncio
async def test_admin_delete_test_run_unknown_email_is_idempotent(client: AsyncClient):
    """Deleting a non-existent email returns 200 with zero counts."""
    r = await client.request(
        "DELETE",
        "/api/v1/admin/demo/test-runs/by-email?email=does-not-exist@example.com",
        headers={"Authorization": f"Bearer {_SUPER_ADMIN}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert all(v == 0 for v in data.values())


@pytest.mark.asyncio
async def test_admin_delete_test_run_rejects_bad_email(client: AsyncClient):
    r = await client.request(
        "DELETE",
        "/api/v1/admin/demo/test-runs/by-email?email=not-an-email",
        headers={"Authorization": f"Bearer {_SUPER_ADMIN}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_delete_test_run_requires_admin_role(client: AsyncClient):
    r = await client.request(
        "DELETE",
        "/api/v1/admin/demo/test-runs/by-email?email=any@example.com",
        headers={"Authorization": f"Bearer {_DEVELOPER}"},
    )
    assert r.status_code == 403
