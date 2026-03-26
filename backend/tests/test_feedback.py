"""
tests/test_feedback.py

Tests for Phase 10 feedback endpoints.

Coverage:
  POST /api/v1/feedback
    - Student submits feedback (201)
    - Rate limit enforced (429 on 6th submission)
    - Invalid category rejected (422)
    - Message too long rejected (422)
    - Unauthenticated returns 403
  GET /api/v1/admin/feedback
    - Admin lists feedback (200)
    - Pagination works
    - Filtering by category, reviewed
    - Non-admin returns 403
    - Unauthenticated returns 403
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token, make_student_token


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _insert_student(client: AsyncClient, student_id: str) -> None:
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, $3, $4, 8, 'en', 'active')
        ON CONFLICT (student_id) DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|feedback-{student_id[:8]}",
        f"Feedback Student {student_id[:6]}",
        f"feedback-{student_id[:6]}@test.invalid",
    )


def _student_id_from_token(token: str) -> str:
    from jose import jwt as _jwt
    payload = _jwt.decode(token, "test-secret-do-not-use-in-production-aaaa", algorithms=["HS256"])
    return payload["student_id"]


async def _submit_feedback(
    client: AsyncClient,
    token: str,
    *,
    category: str = "content",
    message: str = "Great lesson!",
    rating: int | None = 4,
) -> dict:
    r = await client.post(
        "/api/v1/feedback",
        json={
            "category": category,
            "message": message,
            "rating": rating,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return r


# ── POST /feedback ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_feedback_returns_200(client, db_conn, student_token):
    """Valid feedback submission returns 200 with feedback_id."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await _submit_feedback(client, student_token)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "feedback_id" in data
    uuid.UUID(data["feedback_id"])
    assert "submitted_at" in data


@pytest.mark.asyncio
async def test_submit_feedback_with_unit_and_curriculum(client, db_conn, student_token):
    """Feedback can optionally include unit_id and curriculum_id."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await client.post(
        "/api/v1/feedback",
        json={
            "category": "ux",
            "message": "The quiz was confusing.",
            "unit_id": "G8-MATH-001",
            "curriculum_id": "default-2026-g8",
            "rating": 3,
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "feedback_id" in data


@pytest.mark.asyncio
async def test_submit_feedback_general_category(client, db_conn, student_token):
    """All three categories are accepted."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    for category in ("content", "ux", "general"):
        r = await _submit_feedback(client, student_token, category=category)
        assert r.status_code == 200, f"category={category}: {r.text}"


@pytest.mark.asyncio
async def test_submit_feedback_invalid_category_rejected(client, db_conn, student_token):
    """Invalid category returns 422."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await _submit_feedback(client, student_token, category="invalid")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_message_too_long_rejected(client, db_conn, student_token):
    """Messages over 500 chars are rejected with 422."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    r = await _submit_feedback(client, student_token, message="x" * 501)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_rate_limit_enforced(client, db_conn, student_token):
    """After 5 submissions, the 6th returns 429."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    # First 5 should succeed
    for i in range(5):
        r = await _submit_feedback(client, student_token)
        assert r.status_code == 200, f"Attempt {i + 1} failed: {r.text}"

    # 6th should be rate-limited
    r = await _submit_feedback(client, student_token)
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limit_exceeded"


@pytest.mark.asyncio
async def test_submit_feedback_requires_auth(client):
    """Unauthenticated request returns 403."""
    r = await client.post(
        "/api/v1/feedback",
        json={"category": "content", "message": "Test"},
    )
    assert r.status_code == 403


# ── GET /admin/feedback ────────────────────────────────────────────────────────

async def _seed_feedback(client: AsyncClient, student_id: str, *, count: int = 3) -> list[str]:
    """Insert feedback rows directly via pool. Returns list of feedback_ids."""
    pool = client._transport.app.state.pool
    ids = []
    for i in range(count):
        row = await pool.fetchrow(
            """
            INSERT INTO feedback (student_id, category, message, rating)
            VALUES ($1, $2, $3, $4)
            RETURNING feedback_id::text
            """,
            uuid.UUID(student_id),
            ["content", "ux", "general"][i % 3],
            f"Feedback message {i}",
            i % 5 + 1,
        )
        ids.append(row["feedback_id"])
    return ids


@pytest.mark.asyncio
async def test_admin_list_feedback_returns_200(client, db_conn, student_token):
    """Admin can list all feedback items."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    await _seed_feedback(client, student_id, count=3)

    admin_token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/feedback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "pagination" in data
    assert "feedback_items" in data
    assert data["pagination"]["total"] >= 3


@pytest.mark.asyncio
async def test_admin_list_feedback_pagination(client, db_conn, student_token):
    """Pagination limits results per page."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)
    await _seed_feedback(client, student_id, count=5)

    admin_token = make_admin_token(role="super_admin")
    r = await client.get(
        "/api/v1/admin/feedback?page=1&per_page=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["feedback_items"]) <= 2
    assert data["pagination"]["per_page"] == 2


@pytest.mark.asyncio
async def test_admin_list_feedback_filter_by_category(client, db_conn, student_token):
    """Filtering by category returns only matching rows."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    pool = client._transport.app.state.pool
    for cat in ("content", "content", "ux"):
        await pool.execute(
            "INSERT INTO feedback (student_id, category, message) VALUES ($1, $2, $3)",
            uuid.UUID(student_id), cat, f"Test {cat}",
        )

    admin_token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/feedback?category=content",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["feedback_items"]:
        assert item["category"] == "content"


@pytest.mark.asyncio
async def test_admin_list_feedback_filter_by_reviewed(client, db_conn, student_token):
    """Filtering by reviewed=false returns only unreviewed rows."""
    student_id = _student_id_from_token(student_token)
    await _insert_student(client, student_id)

    pool = client._transport.app.state.pool
    await pool.execute(
        "INSERT INTO feedback (student_id, category, message) VALUES ($1, $2, $3)",
        uuid.UUID(student_id), "general", "Unreviewed feedback",
    )

    admin_token = make_admin_token(role="product_admin")
    r = await client.get(
        "/api/v1/admin/feedback?reviewed=false",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["feedback_items"]:
        assert item["reviewed"] is False


@pytest.mark.asyncio
async def test_admin_list_feedback_developer_role_returns_403(client):
    """Developer role does not have feedback:view permission."""
    developer_token = make_admin_token(role="developer")
    r = await client.get(
        "/api/v1/admin/feedback",
        headers={"Authorization": f"Bearer {developer_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_feedback_requires_auth(client):
    """Unauthenticated request returns 403."""
    r = await client.get("/api/v1/admin/feedback")
    assert r.status_code == 403
