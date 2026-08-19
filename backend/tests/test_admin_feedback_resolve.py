"""
tests/test_admin_feedback_resolve.py

Tests for POST /api/v1/admin/feedback/{feedback_id}/resolve (issue #603).

The admin Feedback page has shipped a "Resolve" button since the page was
built, but the endpoint behind it never existed — the click 404'd. Nobody
noticed because the feedback table was empty (#600): no rows meant no buttons
to press. Now that feedback actually arrives, the button is reachable.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token

_TEST_ADMIN_ID = "00000000-0000-0000-0000-000000000099"
_OTHER_ADMIN_ID = "00000000-0000-0000-0000-000000000098"
_STUDENT_ID = "00000000-0000-0000-0000-0000000000f6"


def _headers(role: str = "super_admin", admin_id: str = _TEST_ADMIN_ID) -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=admin_id, role=role)}"}


async def _insert_admin(client: AsyncClient, admin_id: str, email: str) -> None:
    """feedback.reviewed_by has an FK to admin_users, so the actor must exist."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, role, password_hash)
        VALUES ($1, $2, 'super_admin', 'x')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(admin_id),
        email,
    )


async def _insert_student(client: AsyncClient) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'FB Student', 'fb-resolve@test.invalid', 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(_STUDENT_ID),
        f"local:{_STUDENT_ID}",
    )


async def _insert_feedback(client: AsyncClient) -> str:
    await _insert_student(client)
    await _insert_admin(client, _TEST_ADMIN_ID, "fb-resolve-admin@test.invalid")
    await _insert_admin(client, _OTHER_ADMIN_ID, "fb-resolve-other@test.invalid")
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        """
        INSERT INTO feedback (student_id, category, unit_id, helpful, content_type)
        VALUES ($1, 'content', 'G8-MATH-001', TRUE, 'lesson')
        RETURNING feedback_id::text
        """,
        uuid.UUID(_STUDENT_ID),
    )
    return row["feedback_id"]


@pytest.mark.asyncio
async def test_resolve_marks_feedback_reviewed(client, db_conn):
    """Resolving records that it was reviewed, by whom, and when."""
    feedback_id = await _insert_feedback(client)

    r = await client.post(
        f"/api/v1/admin/feedback/{feedback_id}/resolve", headers=_headers()
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["feedback_id"] == feedback_id
    assert body["reviewed"] is True

    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        "SELECT reviewed, reviewed_by::text, reviewed_at FROM feedback WHERE feedback_id = $1",
        uuid.UUID(feedback_id),
    )
    assert row["reviewed"] is True
    assert row["reviewed_by"] == _TEST_ADMIN_ID
    assert row["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_resolve_is_idempotent_and_keeps_the_first_reviewer(client, db_conn):
    """A second click must not error, nor rewrite who actually reviewed it.

    The button has no disabled state while in flight, so a double-click is
    ordinary. Overwriting the reviewer would quietly falsify the audit trail.
    """
    feedback_id = await _insert_feedback(client)

    first = await client.post(
        f"/api/v1/admin/feedback/{feedback_id}/resolve", headers=_headers()
    )
    assert first.status_code == 200, first.text

    pool = client._transport.app.state.pool
    original = await pool.fetchrow(
        "SELECT reviewed_by::text, reviewed_at FROM feedback WHERE feedback_id = $1",
        uuid.UUID(feedback_id),
    )

    second = await client.post(
        f"/api/v1/admin/feedback/{feedback_id}/resolve",
        headers=_headers(admin_id=_OTHER_ADMIN_ID),
    )
    assert second.status_code == 200, second.text

    after = await pool.fetchrow(
        "SELECT reviewed_by::text, reviewed_at FROM feedback WHERE feedback_id = $1",
        uuid.UUID(feedback_id),
    )
    assert after["reviewed_by"] == original["reviewed_by"]
    assert after["reviewed_at"] == original["reviewed_at"]


@pytest.mark.asyncio
async def test_resolve_unknown_id_returns_404(client, db_conn):
    """An id that does not exist is a 404, not a silent success."""
    r = await client.post(
        f"/api/v1/admin/feedback/{uuid.uuid4()}/resolve", headers=_headers()
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_resolve_denied_without_permission(client, db_conn):
    """A developer cannot resolve feedback — the page is gated at product_admin."""
    feedback_id = await _insert_feedback(client)

    r = await client.post(
        f"/api/v1/admin/feedback/{feedback_id}/resolve", headers=_headers(role="developer")
    )
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_resolve_allowed_for_product_admin(client, db_conn):
    """product_admin is the role the page is exposed to."""
    feedback_id = await _insert_feedback(client)

    r = await client.post(
        f"/api/v1/admin/feedback/{feedback_id}/resolve", headers=_headers(role="product_admin")
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_resolve_requires_auth(client, db_conn):
    """No token is rejected."""
    r = await client.post(f"/api/v1/admin/feedback/{uuid.uuid4()}/resolve")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_resolved_feedback_is_filterable(client, db_conn):
    """The list can still be filtered to unreviewed items after resolving.

    This is what the page's filter relies on, so resolving must actually move
    the row out of the unreviewed set.
    """
    feedback_id = await _insert_feedback(client)
    await client.post(f"/api/v1/admin/feedback/{feedback_id}/resolve", headers=_headers())

    r = await client.get(
        "/api/v1/admin/feedback", headers=_headers(), params={"reviewed": "false"}
    )
    assert r.status_code == 200, r.text
    ids = {item["feedback_id"] for item in r.json()["feedback_items"]}
    assert feedback_id not in ids
