"""
tests/test_admin_audit.py

Tests for GET /api/v1/admin/audit (issue #604).

The Audit Log page has been linked from the admin nav and documented as a live
route, but the endpoint behind it was never built — the page's only data source
returned 404. These tests pin the contract the existing client was already
written against (`web/lib/api/admin.ts::getAuditLog`), including the parts the
real data makes unavoidable: 218 of 229 rows on the demo have a NULL target, so
`resource_type`/`resource_id` must be allowed to be absent rather than
pretending every audited action has a target.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token

_TEST_ADMIN_ID = "00000000-0000-0000-0000-000000000099"


def _headers(role: str = "super_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=_TEST_ADMIN_ID, role=role)}"}


async def _insert_audit_row(
    client: AsyncClient,
    event_type: str = "admin_login",
    actor_type: str = "admin",
    target_type: str | None = None,
    target_id: str | None = None,
) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO audit_log (event_type, actor_type, actor_id, target_type, target_id, metadata)
        VALUES ($1, $2, $3::uuid, $4, $5::uuid, '{"note": "test"}'::jsonb)
        """,
        event_type,
        actor_type,
        _TEST_ADMIN_ID,
        target_type,
        target_id,
    )


@pytest.mark.asyncio
async def test_audit_log_returns_entries(client, db_conn):
    """The endpoint exists and returns the shape the admin page consumes."""
    await _insert_audit_row(client, event_type="admin_login")

    r = await client.get("/api/v1/admin/audit", headers=_headers())
    assert r.status_code == 200, r.text
    data = r.json()

    for key in ("entries", "total", "page", "page_size"):
        assert key in data, f"missing {key}"
    assert data["total"] >= 1
    assert data["entries"], "no entries returned"

    entry = data["entries"][0]
    for key in (
        "audit_id",
        "actor_id",
        "actor_role",
        "action",
        "resource_type",
        "resource_id",
        "detail",
        "created_at",
    ):
        assert key in entry, f"entry missing {key}"


@pytest.mark.asyncio
async def test_audit_log_tolerates_rows_with_no_target(client, db_conn):
    """Most audited actions have no target — those rows must still be returned.

    On the demo, 218 of 229 rows have target_id NULL (a login has no resource).
    Requiring a resource would drop or break the majority of the log.
    """
    await _insert_audit_row(client, event_type="password_changed", target_type=None, target_id=None)

    r = await client.get("/api/v1/admin/audit", headers=_headers(), params={"action": "password_changed"})
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert entries, "row with a NULL target was dropped"
    assert entries[0]["resource_id"] is None
    assert entries[0]["resource_type"] is None


@pytest.mark.asyncio
async def test_audit_log_filters_by_action(client, db_conn):
    """The `action` query param filters to that event type only."""
    await _insert_audit_row(client, event_type="admin_login")
    await _insert_audit_row(client, event_type="teacher.capabilities_changed")

    r = await client.get(
        "/api/v1/admin/audit", headers=_headers(), params={"action": "teacher.capabilities_changed"}
    )
    assert r.status_code == 200, r.text
    actions = {e["action"] for e in r.json()["entries"]}
    assert actions == {"teacher.capabilities_changed"}, actions


@pytest.mark.asyncio
async def test_audit_log_paginates(client, db_conn):
    """page/page_size are honoured and echoed back."""
    for _ in range(3):
        await _insert_audit_row(client)

    r = await client.get(
        "/api/v1/admin/audit", headers=_headers(), params={"page": 1, "page_size": 2}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["entries"]) <= 2
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_audit_log_newest_first(client, db_conn):
    """Entries are ordered newest first — an audit log read oldest-first is useless."""
    await _insert_audit_row(client, event_type="first_event")
    await _insert_audit_row(client, event_type="second_event")

    r = await client.get("/api/v1/admin/audit", headers=_headers())
    assert r.status_code == 200, r.text
    timestamps = [e["created_at"] for e in r.json()["entries"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_audit_log_denied_without_permission(client, db_conn):
    """A developer cannot read the audit log.

    The nav gates the page at product_admin; the API must agree, or the
    restriction is cosmetic.
    """
    r = await client.get("/api/v1/admin/audit", headers=_headers(role="developer"))
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_audit_log_allowed_for_product_admin(client, db_conn):
    """product_admin is the role the nav exposes the page to."""
    r = await client.get("/api/v1/admin/audit", headers=_headers(role="product_admin"))
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_audit_log_requires_auth(client, db_conn):
    """No token at all is rejected."""
    r = await client.get("/api/v1/admin/audit")
    assert r.status_code == 401
