"""
tests/test_demo_leads.py

Tests for Epic 7 — Self-Serve Demo Lead System (Option C).

Design: all state setup is done via API calls (not db_conn inserts), because
the endpoint pool and db_conn use separate transactions and can't see each other's
uncommitted data.  db_conn is used only for READ verification after API writes.

Coverage:
  DML-01  POST /demo/tour/request — happy path → 202 pending
  DML-02  POST /demo/tour/request — geo-blocked country → 403
  DML-03  POST /demo/tour/request — email already has active demo → 409
  DML-04  POST /demo/tour/request — missing required field → 422
  DML-05  GET  /admin/demo-leads — no auth → 401/403
  DML-06  GET  /admin/demo-leads — plat_admin sees leads
  DML-07  GET  /admin/demo-leads — filter by status
  DML-08  POST /admin/demo-leads/{id}/approve — generates tour URLs
  DML-09  POST /admin/demo-leads/{id}/approve — unknown lead → 404
  DML-10  POST /admin/demo-leads/{id}/reject  — marks rejected
  DML-11  GET  /admin/demo-geo-blocks — returns list
  DML-12  POST /admin/demo-geo-blocks — add block → 201
  DML-13  POST /admin/demo-geo-blocks — duplicate add → added=False
  DML-14  DELETE /admin/demo-geo-blocks/{cc} — remove block
  DML-15  DELETE /admin/demo-geo-blocks/{cc} — unknown code → 404
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import TEST_DB_URL
from tests.helpers.token_factory import _DEFAULT_ADMIN_ID, make_admin_token


# ── Module-scoped fixture: seed the test plat_admin user ─────────────────────
# demo_geo_blocks.added_by and demo_leads.approved_by are FKs → admin_users.
# The JWT token used in tests carries admin_id = _DEFAULT_ADMIN_ID which must
# exist in admin_users for FK constraints to pass.
# Uses synchronous psycopg2 (not asyncpg) to avoid event-loop scope conflicts
# with pytest-asyncio's session-scoped event_loop fixture.


@pytest.fixture(scope="module", autouse=True)
def seed_plat_admin():
    """Insert the default test admin user before any test in this module runs."""
    plain_url = TEST_DB_URL.replace("+asyncpg", "")
    conn = psycopg2.connect(plain_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO admin_users (admin_user_id, email, password_hash, role)
            VALUES (%s, 'test-plat-admin@example.com', '$2b$12$fakehash_for_tests_only', 'plat_admin')
            ON CONFLICT (admin_user_id) DO NOTHING
            """,
            (_DEFAULT_ADMIN_ID,),
        )
    conn.close()
    yield
    conn = psycopg2.connect(plain_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM admin_users WHERE admin_user_id = %s",
            (_DEFAULT_ADMIN_ID,),
        )
    conn.close()

# ── Auth helpers ──────────────────────────────────────────────────────────────

PLAT_ADMIN_TOKEN = make_admin_token(role="plat_admin")


def _plat_auth() -> dict:
    return {"Authorization": f"Bearer {PLAT_ADMIN_TOKEN}"}


# ── Lead request helpers ──────────────────────────────────────────────────────

def _lead_body(suffix: str) -> dict:
    return {
        "name": f"Test User {suffix}",
        "email": f"demo_{suffix}@example.com",
        "school_org": f"Test School {suffix}",
    }


async def _create_lead(client: AsyncClient, suffix: str) -> str:
    """Create a pending lead via API and return its lead_id."""
    r = await client.post("/api/v1/demo/tour/request", json=_lead_body(suffix))
    assert r.status_code == 202, f"Lead creation failed: {r.text}"
    # Retrieve the lead_id via the admin list endpoint
    listing = await client.get(
        "/api/v1/admin/demo-leads?status=pending",
        headers=_plat_auth(),
    )
    assert listing.status_code == 200, listing.text
    leads = listing.json()["leads"]
    email = f"demo_{suffix}@example.com"
    matching = [l for l in leads if l["email"] == email]
    assert matching, f"Lead for {email} not found in listing"
    return matching[-1]["lead_id"]


async def _add_geo_block(client: AsyncClient, code: str) -> None:
    r = await client.post(
        "/api/v1/admin/demo-geo-blocks",
        json={"country_code": code, "country_name": f"Country {code}"},
        headers=_plat_auth(),
    )
    assert r.status_code == 201, f"Geo block add failed: {r.text}"


async def _remove_geo_block(client: AsyncClient, code: str) -> None:
    await client.delete(f"/api/v1/admin/demo-geo-blocks/{code}", headers=_plat_auth())


# ── DML-01: happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_request_happy_path(client: AsyncClient):
    """POST /demo/tour/request with valid body returns 202 and status=pending."""
    r = await client.post("/api/v1/demo/tour/request", json=_lead_body("happy"))
    assert r.status_code == 202, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert "message" in data


# ── DML-02: geo-blocked ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_request_geo_blocked(client: AsyncClient):
    """POST /demo/tour/request from a blocked country returns 403 geo_blocked."""
    await _add_geo_block(client, "XV")
    try:
        r = await client.post(
            "/api/v1/demo/tour/request",
            json=_lead_body("geo"),
            headers={"CF-IPCountry": "XV"},
        )
        assert r.status_code == 403, r.text
        assert r.json()["error"] == "geo_blocked"
    finally:
        await _remove_geo_block(client, "XV")


# ── DML-03: active demo exists ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_request_active_demo_exists(client: AsyncClient):
    """Second request from same email when one is already approved → 409."""
    email = "active_test@example.com"
    body = {"name": "Active User", "email": email, "school_org": "Test School"}

    # Create a lead
    r1 = await client.post("/api/v1/demo/tour/request", json=body)
    assert r1.status_code == 202, r1.text

    # Get the lead_id
    listing = await client.get("/api/v1/admin/demo-leads?status=pending", headers=_plat_auth())
    leads = listing.json()["leads"]
    lead = next((l for l in leads if l["email"] == email), None)
    assert lead is not None, "Lead not found"

    # Approve it
    with patch("src.demo_leads.router.send_demo_approval_email", new_callable=AsyncMock):
        approve = await client.post(
            f"/api/v1/admin/demo-leads/{lead['lead_id']}/approve",
            json={"ttl_hours": 24},
            headers=_plat_auth(),
        )
    assert approve.status_code == 200, approve.text

    # Request again from same email → 409
    r2 = await client.post("/api/v1/demo/tour/request", json=body)
    assert r2.status_code == 409, r2.text
    assert r2.json()["error"] == "active_demo_exists"


# ── DML-04: missing field ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_demo_request_missing_field(client: AsyncClient):
    """POST without school_org returns 422."""
    r = await client.post(
        "/api/v1/demo/tour/request",
        json={"name": "No Org", "email": "norg@example.com"},
    )
    assert r.status_code == 422


# ── DML-05: admin endpoint requires auth ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_demo_leads_no_auth(client: AsyncClient):
    """GET /admin/demo-leads without JWT returns 401 or 403."""
    r = await client.get("/api/v1/admin/demo-leads")
    assert r.status_code in (401, 403)


# ── DML-06: plat_admin sees leads ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_demo_leads_plat_admin(client: AsyncClient):
    """GET /admin/demo-leads returns the leads list for a plat_admin token."""
    # Create a lead to ensure there's something to list
    r = await client.post("/api/v1/demo/tour/request", json=_lead_body("list01"))
    assert r.status_code == 202, r.text

    listing = await client.get("/api/v1/admin/demo-leads", headers=_plat_auth())
    assert listing.status_code == 200, listing.text
    data = listing.json()
    assert "leads" in data
    assert "total" in data
    assert data["total"] >= 1


# ── DML-07: status filter ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_demo_leads_filter_by_status(client: AsyncClient):
    """GET /admin/demo-leads?status=pending only returns pending leads."""
    # Ensure at least one pending lead exists
    await client.post("/api/v1/demo/tour/request", json=_lead_body("filter01"))

    r = await client.get("/api/v1/admin/demo-leads?status=pending", headers=_plat_auth())
    assert r.status_code == 200, r.text
    leads = r.json()["leads"]
    assert all(l["status"] == "pending" for l in leads)


# ── DML-08: approve ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_demo_lead(client: AsyncClient, db_conn):
    """POST /admin/demo-leads/{id}/approve sets status=approved and returns tour URLs."""
    lead_id = await _create_lead(client, "approve01")

    with patch("src.demo_leads.router.send_demo_approval_email", new_callable=AsyncMock):
        r = await client.post(
            f"/api/v1/admin/demo-leads/{lead_id}/approve",
            json={"ttl_hours": 24},
            headers=_plat_auth(),
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["lead_id"] == lead_id
    assert "demo_url_admin" in data
    assert "demo_url_teacher" in data
    assert "demo_url_student" in data
    assert "demo_token=" in data["demo_url_admin"]
    assert "token_expires_at" in data

    # Verify DB state via the listing API
    listing = await client.get(f"/api/v1/admin/demo-leads?status=approved", headers=_plat_auth())
    approved = [l for l in listing.json()["leads"] if l["lead_id"] == lead_id]
    assert approved, "Lead not found in approved list"
    assert approved[0]["status"] == "approved"


# ── DML-09: approve unknown lead ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_unknown_lead(client: AsyncClient):
    """POST approve for a non-existent lead_id returns 404."""
    fake_id = str(uuid.uuid4())
    with patch("src.demo_leads.router.send_demo_approval_email", new_callable=AsyncMock):
        r = await client.post(
            f"/api/v1/admin/demo-leads/{fake_id}/approve",
            json={"ttl_hours": 24},
            headers=_plat_auth(),
        )
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not_found"


# ── DML-10: reject ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_demo_lead(client: AsyncClient):
    """POST /admin/demo-leads/{id}/reject sets status=rejected."""
    lead_id = await _create_lead(client, "reject01")

    r = await client.post(
        f"/api/v1/admin/demo-leads/{lead_id}/reject",
        json={"reason": "Out of target region"},
        headers=_plat_auth(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "rejected"
    assert data["lead_id"] == lead_id

    # Verify via listing
    listing = await client.get("/api/v1/admin/demo-leads?status=rejected", headers=_plat_auth())
    rejected = [l for l in listing.json()["leads"] if l["lead_id"] == lead_id]
    assert rejected, "Lead not found in rejected list"


# ── DML-11: geo-blocks list ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_geo_blocks_empty(client: AsyncClient):
    """GET /admin/demo-geo-blocks returns a blocks list."""
    r = await client.get("/api/v1/admin/demo-geo-blocks", headers=_plat_auth())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "blocks" in data
    assert isinstance(data["blocks"], list)


# ── DML-12: add geo block ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_geo_block(client: AsyncClient):
    """POST /admin/demo-geo-blocks → 201 with added=True."""
    code = "ZZ"
    r = await client.post(
        "/api/v1/admin/demo-geo-blocks",
        json={"country_code": code, "country_name": "Zeta Land"},
        headers=_plat_auth(),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["country_code"] == code
    assert data["added"] is True

    # Cleanup
    await _remove_geo_block(client, code)


# ── DML-13: duplicate add → added=False ──────────────────────────────────────


@pytest.mark.asyncio
async def test_add_geo_block_duplicate(client: AsyncClient):
    """Adding the same country code a second time returns added=False."""
    code = "YY"
    # Add it the first time
    r1 = await client.post(
        "/api/v1/admin/demo-geo-blocks",
        json={"country_code": code, "country_name": "Ypsilon"},
        headers=_plat_auth(),
    )
    assert r1.status_code == 201, r1.text

    # Add the same code again
    r2 = await client.post(
        "/api/v1/admin/demo-geo-blocks",
        json={"country_code": code, "country_name": "Ypsilon"},
        headers=_plat_auth(),
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["added"] is False

    # Cleanup
    await _remove_geo_block(client, code)


# ── DML-14: remove geo block ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_geo_block(client: AsyncClient):
    """DELETE /admin/demo-geo-blocks/{cc} removes the block."""
    code = "WW"
    await _add_geo_block(client, code)

    r = await client.delete(f"/api/v1/admin/demo-geo-blocks/{code}", headers=_plat_auth())
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "removed"
    assert data["country_code"] == code


# ── DML-15: remove unknown geo block ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_geo_block_not_found(client: AsyncClient):
    """DELETE on a non-existent country code returns 404."""
    r = await client.delete("/api/v1/admin/demo-geo-blocks/QQ", headers=_plat_auth())
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not_found"
