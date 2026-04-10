"""
tests/test_admin.py

Tests for Phase 7 admin endpoints.

Coverage:
  - GET  /admin/pipeline/status          — requires review:read
  - GET  /admin/content/review/queue     — requires review:read; filters work
  - POST /admin/content/review/{id}/open — requires review:annotate
  - POST /admin/content/review/{id}/annotate — requires review:annotate
  - DELETE /admin/content/review/annotations/{id} — 404 on unknown id
  - POST /admin/content/review/{id}/rate  — requires review:rate (1–5 validated)
  - POST /admin/content/review/{id}/approve — requires review:approve; sets status=approved
  - POST /admin/content/review/{id}/reject  — requires review:approve; regenerate dispatched
  - POST /admin/content/review/batch-approve — approves all pending for a curriculum
  - POST /admin/content/review/{id}/assign  — requires review:assign; assigns/unassigns reviewer
  - GET  /admin/users                     — requires review:assign; lists active admin accounts
  - GET  /admin/content/review/queue (assigned_to filter) — returns only assigned items
  - POST /admin/content/versions/{id}/publish  — requires content:publish; sets published
  - POST /admin/content/versions/{id}/rollback — requires content:rollback
  - POST /admin/content/block             — requires content:block; returns block_id
  - DELETE /admin/content/block/{id}      — unblocks; 404 on unknown
  - GET  /admin/content/{unit_id}/feedback/marked — requires review:read
  - GET  /admin/analytics/subscription    — returns MRR metrics
  - GET  /admin/analytics/struggle        — returns struggle list
  - GET  /admin/content/dictionary        — returns synonyms/antonyms
  - Auth: student token rejected on all admin endpoints (401 — wrong secret)
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_admin_token, make_student_token


# ── Helpers ───────────────────────────────────────────────────────────────────

# Fixed admin UUID so the JWT and the DB row always reference the same admin.
_TEST_ADMIN_ID = "00000000-0000-0000-0000-000000000099"


def _admin_headers(role: str = "super_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(admin_id=_TEST_ADMIN_ID, role=role)}"}


def _student_headers() -> dict:
    return {"Authorization": f"Bearer {make_student_token()}"}


async def _insert_version(
    client: AsyncClient,
    curriculum_id: str = "default-2026-g8",
    subject: str = "Mathematics",
    status: str = "ready_for_review",
    alex_warnings_count: int = 0,
) -> str:
    """Insert a content_subject_versions row; return version_id."""
    pool = client._transport.app.state.pool
    row = await pool.fetchrow(
        """
        INSERT INTO content_subject_versions
            (curriculum_id, subject, version_number, status, alex_warnings_count)
        VALUES ($1, $2, 1, $3, $4)
        ON CONFLICT DO NOTHING
        RETURNING version_id::text
        """,
        curriculum_id, subject, status, alex_warnings_count,
    )
    if row:
        return row["version_id"]
    # conflict — fetch existing
    row = await pool.fetchrow(
        "SELECT version_id::text FROM content_subject_versions WHERE curriculum_id=$1 AND subject=$2 ORDER BY version_number DESC LIMIT 1",
        curriculum_id, subject,
    )
    return row["version_id"]


async def _insert_admin(client: AsyncClient) -> str:
    """Insert an admin_users row using the fixed test admin ID."""
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO admin_users (admin_user_id, email, role, password_hash)
        VALUES ($1, 'test-admin@test.invalid', 'super_admin', 'x')
        ON CONFLICT (admin_user_id) DO NOTHING
        """,
        uuid.UUID(_TEST_ADMIN_ID),
    )
    return _TEST_ADMIN_ID


async def _insert_student(client: AsyncClient) -> str:
    """Insert a student row; return student_id."""
    student_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO students (student_id, external_auth_id, name, email, grade, locale, account_status)
        VALUES ($1, $2, 'Test Student', $3, 8, 'en', 'active')
        ON CONFLICT DO NOTHING
        """,
        uuid.UUID(student_id),
        f"auth0|admin-test-{student_id[:8]}",
        f"student-{student_id[:8]}@test.invalid",
    )
    return student_id


# ── Pipeline status ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_status_returns_counts(client, db_conn):
    """GET /admin/pipeline/status returns version counts."""
    await _insert_version(client, subject=f"Sci-{uuid.uuid4().hex[:6]}")

    r = await client.get("/api/v1/admin/pipeline/status", headers=_admin_headers())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total_versions" in data
    assert "ready_for_review" in data
    assert "published" in data


@pytest.mark.asyncio
async def test_pipeline_status_requires_auth(client):
    r = await client.get("/api/v1/admin/pipeline/status", headers=_student_headers())
    assert r.status_code == 401


# ── Review queue ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_queue_returns_items(client, db_conn):
    """GET /admin/content/review/queue returns matching versions."""
    subject = f"Queue-{uuid.uuid4().hex[:6]}"
    await _insert_version(client, subject=subject)

    r = await client.get(
        "/api/v1/admin/content/review/queue",
        params={"subject": subject},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] >= 1
    assert any(item["subject"] == subject for item in data["items"])


@pytest.mark.asyncio
async def test_review_queue_status_filter(client, db_conn):
    """Status filter returns only versions with matching status."""
    subject = f"Filt-{uuid.uuid4().hex[:6]}"
    await _insert_version(client, subject=subject, status="approved")

    r = await client.get(
        "/api/v1/admin/content/review/queue",
        params={"status": "approved", "subject": subject},
        headers=_admin_headers(),
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["status"] == "approved"


# ── Open review ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_open_review_session(client, db_conn):
    """POST /admin/content/review/{id}/open creates a review row and returns review_id."""
    version_id = await _insert_version(client, subject=f"Open-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/open",
        json={"notes": "Starting review."},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "review_id" in data
    assert data["action"] == "open"
    assert data["version_id"] == version_id


# ── Annotate ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_annotate_creates_annotation(client, db_conn):
    """POST annotate returns annotation_id."""
    version_id = await _insert_version(client, subject=f"Ann-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/annotate",
        json={
            "unit_id": "G8-MATH-001",
            "content_type": "lesson",
            "marked_text": "confusing phrase",
            "annotation_text": "Rephrase for clarity.",
            "start_offset": 10,
            "end_offset": 26,
        },
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "annotation_id" in data
    assert data["annotation_text"] == "Rephrase for clarity."


@pytest.mark.asyncio
async def test_delete_annotation_404_on_unknown(client, db_conn):
    """DELETE annotations/{id} returns 404 for unknown annotation."""
    r = await client.delete(
        f"/api/v1/admin/content/review/annotations/{uuid.uuid4()}",
        headers=_admin_headers(),
    )
    assert r.status_code == 404


# ── Rate ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_version(client, db_conn):
    """POST /rate inserts a review row with ratings."""
    version_id = await _insert_version(client, subject=f"Rate-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/rate",
        json={"language_rating": 4, "content_rating": 5},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["language_rating"] == 4
    assert data["content_rating"] == 5


@pytest.mark.asyncio
async def test_rate_validates_range(client, db_conn):
    """Ratings outside 1–5 return 422."""
    version_id = await _insert_version(client, subject=f"RateV-{uuid.uuid4().hex[:6]}")
    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/rate",
        json={"language_rating": 0, "content_rating": 6},
        headers=_admin_headers(),
    )
    assert r.status_code == 422


# ── Approve ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_version(client, db_conn):
    """POST /approve sets version status to approved."""
    version_id = await _insert_version(client, subject=f"Appr-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/approve",
        json={"notes": "LGTM"},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


# ── Reject ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_version(client, db_conn):
    """POST /reject sets version status to rejected; regenerate=False."""
    version_id = await _insert_version(client, subject=f"Rej-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/reject",
        json={"notes": "Too many errors.", "regenerate": False},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "rejected"
    assert data["regenerating"] is False


@pytest.mark.asyncio
async def test_reject_with_regenerate_dispatches_task(client, db_conn):
    """POST /reject with regenerate=True dispatches regenerate_subject_task."""
    version_id = await _insert_version(client, subject=f"RejR-{uuid.uuid4().hex[:6]}")
    await _insert_admin(client)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None) as mock_send:
        r = await client.post(
            f"/api/v1/admin/content/review/{version_id}/reject",
            json={"notes": "Regenerate please.", "regenerate": True},
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    assert r.json()["regenerating"] is True
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "src.auth.tasks.regenerate_subject_task"


# ── Batch approve ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_approve_approves_all_pending(client, db_conn):
    """POST /batch-approve sets all pending versions for a curriculum to approved."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    await _insert_admin(client)

    # Insert three pending versions for the same curriculum
    subjects = [f"Batch-{uuid.uuid4().hex[:6]}" for _ in range(3)]
    for subject in subjects:
        await _insert_version(client, curriculum_id=curriculum_id, subject=subject, status="pending")

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            "/api/v1/admin/content/review/batch-approve",
            json={"curriculum_id": curriculum_id, "notes": "Batch LGTM"},
            headers=_admin_headers(),
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["approved_count"] == 3
    assert len(data["version_ids"]) == 3
    assert data["skipped"] == []

    # Verify all rows are now approved in the DB
    pool = client._transport.app.state.pool
    still_pending = await pool.fetchval(
        "SELECT COUNT(*) FROM content_subject_versions WHERE curriculum_id = $1 AND status = 'pending'",
        curriculum_id,
    )
    assert still_pending == 0


@pytest.mark.asyncio
async def test_batch_approve_skips_non_pending(client, db_conn):
    """Batch approve only touches pending versions — approved/published are left alone."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    await _insert_admin(client)

    pending_subject = f"BatchPend-{uuid.uuid4().hex[:6]}"
    approved_subject = f"BatchAppr-{uuid.uuid4().hex[:6]}"
    await _insert_version(client, curriculum_id=curriculum_id, subject=pending_subject, status="pending")
    await _insert_version(client, curriculum_id=curriculum_id, subject=approved_subject, status="approved")

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            "/api/v1/admin/content/review/batch-approve",
            json={"curriculum_id": curriculum_id},
            headers=_admin_headers(),
        )

    assert r.status_code == 200, r.text
    data = r.json()
    # Only the one pending version should be approved
    assert data["approved_count"] == 1

    # The already-approved version should remain approved (not double-approved)
    pool = client._transport.app.state.pool
    approved_count = await pool.fetchval(
        "SELECT COUNT(*) FROM content_subject_versions WHERE curriculum_id = $1 AND status = 'approved'",
        curriculum_id,
    )
    assert approved_count == 2  # original approved + the newly approved one


@pytest.mark.asyncio
async def test_batch_approve_empty_returns_zero(client, db_conn):
    """Batch approve for a curriculum with no pending versions returns approved_count=0."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    await _insert_admin(client)
    # Insert a non-pending version so the curriculum exists
    await _insert_version(client, curriculum_id=curriculum_id,
                           subject=f"Pub-{uuid.uuid4().hex[:6]}", status="published")

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            "/api/v1/admin/content/review/batch-approve",
            json={"curriculum_id": curriculum_id},
            headers=_admin_headers(),
        )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["approved_count"] == 0
    assert data["version_ids"] == []
    assert data["skipped"] == []


@pytest.mark.asyncio
async def test_batch_approve_skips_versions_with_warnings(client, db_conn):
    """Pending versions with alex_warnings_count > 0 are skipped and reported."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    await _insert_admin(client)

    clean_subject = f"Clean-{uuid.uuid4().hex[:6]}"
    dirty_subject = f"Dirty-{uuid.uuid4().hex[:6]}"
    await _insert_version(
        client, curriculum_id=curriculum_id, subject=clean_subject,
        status="pending", alex_warnings_count=0,
    )
    dirty_vid = await _insert_version(
        client, curriculum_id=curriculum_id, subject=dirty_subject,
        status="pending", alex_warnings_count=3,
    )

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            "/api/v1/admin/content/review/batch-approve",
            json={"curriculum_id": curriculum_id},
            headers=_admin_headers(),
        )

    assert r.status_code == 200, r.text
    data = r.json()
    # Only the clean version is approved
    assert data["approved_count"] == 1
    assert len(data["version_ids"]) == 1
    # The dirty version is reported as skipped
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["version_id"] == dirty_vid
    assert "warning" in data["skipped"][0]["reason"].lower()

    # Dirty version remains pending in the DB
    pool = client._transport.app.state.pool
    dirty_status = await pool.fetchval(
        "SELECT status FROM content_subject_versions WHERE version_id = $1::uuid",
        dirty_vid,
    )
    assert dirty_status == "pending"


@pytest.mark.asyncio
async def test_batch_approve_requires_approve_permission(client, db_conn):
    """Developer role (lacks review:approve) receives 403."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"

    r = await client.post(
        "/api/v1/admin/content/review/batch-approve",
        json={"curriculum_id": curriculum_id, "notes": "test"},
        headers=_admin_headers(role="developer"),
    )
    assert r.status_code == 403


# ── Assign ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_version_to_admin(client, db_conn):
    """POST /assign sets assigned_to_admin_id and returns assigned_to_email."""
    version_id = await _insert_version(
        client, subject=f"Assign-{uuid.uuid4().hex[:6]}", status="pending"
    )
    await _insert_admin(client)

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/review/{version_id}/assign",
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["version_id"] == version_id
    assert data["assigned_to_admin_id"] == _TEST_ADMIN_ID
    assert data["assigned_to_email"] == "test-admin@test.invalid"
    assert data["assigned_at"] is not None


@pytest.mark.asyncio
async def test_unassign_version(client, db_conn):
    """POST /assign with admin_id=null clears the assignment."""
    version_id = await _insert_version(
        client, subject=f"Unassign-{uuid.uuid4().hex[:6]}", status="pending"
    )
    await _insert_admin(client)

    # First assign
    with patch("src.core.events.write_audit_log"):
        await client.post(
            f"/api/v1/admin/content/review/{version_id}/assign",
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(),
        )
    # Then unassign
    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/review/{version_id}/assign",
            json={"admin_id": None},
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assigned_to_admin_id"] is None
    assert data["assigned_to_email"] is None
    assert data["assigned_at"] is None


@pytest.mark.asyncio
async def test_assign_version_404_on_unknown(client, db_conn):
    """POST /assign on a non-existent version returns 404."""
    await _insert_admin(client)
    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/review/{uuid.uuid4()}/assign",
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(),
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_assign_version_requires_permission(client, db_conn):
    """developer role lacks review:annotate — must get 403 even for self-assign."""
    version_id = await _insert_version(
        client, subject=f"AssignPerm-{uuid.uuid4().hex[:6]}", status="pending"
    )
    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/assign",
        json={"admin_id": _TEST_ADMIN_ID},
        headers=_admin_headers(role="developer"),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_self_assign_allowed_for_annotate_role(client, db_conn):
    """tester role (has review:annotate) can assign the version to themselves."""
    version_id = await _insert_version(
        client, subject=f"SelfAssign-{uuid.uuid4().hex[:6]}", status="pending"
    )
    await _insert_admin(client)

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/review/{version_id}/assign",
            # Assigning to the same admin_id as the JWT (self-assign)
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(role="tester"),
        )
    assert r.status_code == 200, r.text
    assert r.json()["assigned_to_admin_id"] == _TEST_ADMIN_ID


@pytest.mark.asyncio
async def test_assign_other_requires_assign_permission(client, db_conn):
    """tester cannot assign to a *different* admin — requires review:assign."""
    version_id = await _insert_version(
        client, subject=f"AssignOther-{uuid.uuid4().hex[:6]}", status="pending"
    )
    other_admin_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/admin/content/review/{version_id}/assign",
        json={"admin_id": other_admin_id},
        headers=_admin_headers(role="tester"),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_queue_unassigned_filter(client, db_conn):
    """assigned_to=unassigned returns only versions with no assignee."""
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    await _insert_admin(client)

    unassigned_vid = await _insert_version(
        client, curriculum_id=curriculum_id,
        subject=f"Unassigned-{uuid.uuid4().hex[:6]}", status="pending",
    )
    assigned_vid = await _insert_version(
        client, curriculum_id=curriculum_id,
        subject=f"Assigned-{uuid.uuid4().hex[:6]}", status="pending",
    )
    # Assign one of them
    with patch("src.core.events.write_audit_log"):
        await client.post(
            f"/api/v1/admin/content/review/{assigned_vid}/assign",
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(),
        )

    r = await client.get(
        "/api/v1/admin/content/review/queue",
        params={"curriculum_id": curriculum_id, "assigned_to": "unassigned"},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    ids = [item["version_id"] for item in r.json()["items"]]
    assert unassigned_vid in ids
    assert assigned_vid not in ids


@pytest.mark.asyncio
async def test_list_admin_users(client, db_conn):
    """GET /admin/users returns list of active admin accounts."""
    await _insert_admin(client)
    r = await client.get("/api/v1/admin/users", headers=_admin_headers())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "users" in data
    emails = [u["email"] for u in data["users"]]
    assert "test-admin@test.invalid" in emails


@pytest.mark.asyncio
async def test_queue_assigned_to_filter(client, db_conn):
    """GET /queue?assigned_to=<id> returns only versions assigned to that admin."""
    await _insert_admin(client)
    curriculum_id = f"default-2026-g{uuid.uuid4().hex[:4]}"
    assigned_id = await _insert_version(
        client,
        curriculum_id=curriculum_id,
        subject=f"Assigned-{uuid.uuid4().hex[:6]}",
        status="pending",
    )
    unassigned_id = await _insert_version(
        client,
        curriculum_id=curriculum_id,
        subject=f"Unassigned-{uuid.uuid4().hex[:6]}",
        status="pending",
    )

    # Assign the first version to the test admin
    with patch("src.core.events.write_audit_log"):
        await client.post(
            f"/api/v1/admin/content/review/{assigned_id}/assign",
            json={"admin_id": _TEST_ADMIN_ID},
            headers=_admin_headers(),
        )

    r = await client.get(
        "/api/v1/admin/content/review/queue",
        params={"assigned_to": _TEST_ADMIN_ID},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    ids = [item["version_id"] for item in r.json()["items"]]
    assert assigned_id in ids
    assert unassigned_id not in ids


# ── Publish ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_version(client, db_conn):
    """POST /publish sets status=published and returns published_at."""
    version_id = await _insert_version(
        client, subject=f"Pub-{uuid.uuid4().hex[:6]}", status="approved"
    )
    await _insert_admin(client)

    with patch("src.admin.service._invalidate_cdn"), \
         patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/versions/{version_id}/publish",
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "published"
    assert "published_at" in data


@pytest.mark.asyncio
async def test_publish_404_on_unknown(client, db_conn):
    r = await client.post(
        f"/api/v1/admin/content/versions/{uuid.uuid4()}/publish",
        headers=_admin_headers(),
    )
    assert r.status_code == 404


# ── Rollback ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rollback_version(client, db_conn):
    """POST /rollback un-publishes the current version (moves it back to approved)."""
    version_id = await _insert_version(
        client, subject=f"Roll-{uuid.uuid4().hex[:6]}", status="published"
    )
    await _insert_admin(client)

    with patch("src.admin.service._invalidate_cdn"), \
         patch("src.core.events.write_audit_log"):
        r = await client.post(
            f"/api/v1/admin/content/versions/{version_id}/rollback",
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


# ── Content block ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_block_content(client, db_conn):
    """POST /admin/content/block creates a block and returns block_id."""
    await _insert_admin(client)

    with patch("src.core.events.write_audit_log"):
        r = await client.post(
            "/api/v1/admin/content/block",
            json={
                "curriculum_id": "default-2026-g8",
                "unit_id": f"G8-MATH-{uuid.uuid4().hex[:6]}",
                "content_type": "lesson",
                "reason": "Inappropriate content",
            },
            headers=_admin_headers(),
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "block_id" in data
    assert data["content_type"] == "lesson"


@pytest.mark.asyncio
async def test_unblock_404_on_unknown(client, db_conn):
    r = await client.delete(
        f"/api/v1/admin/content/block/{uuid.uuid4()}",
        headers=_admin_headers(),
    )
    assert r.status_code == 404


# ── Student feedback ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_feedback_marked_returns_empty(client, db_conn):
    """GET feedback/marked returns empty list for unit with no feedback."""
    r = await client.get(
        "/api/v1/admin/content/G8-NO-FEEDBACK/feedback/marked",
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_feedback_marked_returns_entries(client, db_conn):
    """GET feedback/marked returns submitted feedback items."""
    student_id = await _insert_student(client)
    unit_id = f"G8-SCI-{uuid.uuid4().hex[:6]}"
    pool = client._transport.app.state.pool
    await pool.execute(
        """
        INSERT INTO student_content_feedback
            (student_id, unit_id, curriculum_id, content_type, category, message)
        VALUES ($1, $2, 'default-2026-g8', 'lesson', 'incorrect', 'Wrong formula')
        """,
        uuid.UUID(student_id), unit_id,
    )

    r = await client.get(
        f"/api/v1/admin/content/{unit_id}/feedback/marked",
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "incorrect"


# ── Feedback report (units exceeding threshold) ───────────────────────────────

@pytest.mark.asyncio
async def test_feedback_report_returns_empty_below_threshold(client, db_conn):
    """GET feedback/report returns empty list when no unit reaches the threshold."""
    r = await client.get(
        "/api/v1/admin/content/feedback/report",
        params={"threshold": 10},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "threshold" in data
    assert data["threshold"] == 10


@pytest.mark.asyncio
async def test_feedback_report_surfaces_units_at_threshold(client, db_conn):
    """Units with feedback_count >= threshold appear in the report."""
    student_id = await _insert_student(client)
    unit_id = f"G8-RPT-{uuid.uuid4().hex[:6]}"
    pool = client._transport.app.state.pool
    # Insert 3 feedback rows for the same unit
    for category in ("incorrect", "confusing", "incorrect"):
        await pool.execute(
            """
            INSERT INTO student_content_feedback
                (student_id, unit_id, curriculum_id, content_type, category)
            VALUES ($1, $2, 'default-2026-g8', 'lesson', $3)
            """,
            uuid.UUID(student_id), unit_id, category,
        )

    r = await client.get(
        "/api/v1/admin/content/feedback/report",
        params={"threshold": 3},
        headers=_admin_headers(),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    matching = [item for item in data["items"] if item["unit_id"] == unit_id]
    assert len(matching) == 1
    item = matching[0]
    assert item["report_count"] == 3
    assert item["incorrect_count"] == 2
    assert item["confusing_count"] == 1
    assert item["other_count"] == 0


# ── Subscription analytics ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_analytics_returns_structure(client, db_conn):
    """GET /admin/analytics/subscription returns expected fields."""
    r = await client.get("/api/v1/admin/analytics/subscription", headers=_admin_headers())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "mrr_usd" in data
    assert "total_active" in data
    assert "churn_rate" in data
    assert "new_this_month" in data


# ── Struggle analytics ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_struggle_analytics_returns_structure(client, db_conn):
    """GET /admin/analytics/struggle returns items list."""
    r = await client.get("/api/v1/admin/analytics/struggle", headers=_admin_headers())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)


# ── Dictionary ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dictionary_returns_structure(client, db_conn):
    """GET /admin/content/dictionary returns word + synonyms + antonyms."""
    with patch("src.admin.service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_syn_resp = MagicMock()
        mock_syn_resp.status_code = 200
        mock_syn_resp.json.return_value = [{"word": "happy"}, {"word": "joyful"}]

        mock_ant_resp = MagicMock()
        mock_ant_resp.status_code = 200
        mock_ant_resp.json.return_value = [{"word": "sad"}]

        mock_client.get = AsyncMock(side_effect=[mock_syn_resp, mock_ant_resp])

        r = await client.get(
            "/api/v1/admin/content/dictionary",
            params={"word": "glad"},
            headers=_admin_headers(),
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["word"] == "glad"
    assert "synonyms" in data
    assert "antonyms" in data
    assert "definitions" in data


@pytest.mark.asyncio
async def test_dictionary_requires_auth(client):
    r = await client.get("/api/v1/admin/content/dictionary", params={"word": "test"})
    assert r.status_code == 401


# ── Student token rejected on admin endpoints ────────────────────────────────

@pytest.mark.asyncio
async def test_student_token_rejected(client):
    """Student JWTs must not access admin endpoints (signature fails → 401)."""
    hdrs = _student_headers()
    r1 = await client.get("/api/v1/admin/pipeline/status", headers=hdrs)
    r2 = await client.get("/api/v1/admin/content/review/queue", headers=hdrs)
    r3 = await client.get("/api/v1/admin/analytics/subscription", headers=hdrs)
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
