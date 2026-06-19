"""
tests/test_feedback_460_462.py

Regression tests for two QA-cycle feedback fixes (2026-06-14):

  #460 — Quiz score must never exceed the number of questions. `end_session`
         clamps score to [0, total] so impossible results (e.g. 8/5 = 160%)
         can never be persisted.

  #462 — Subject must resolve to a human-readable display name, not the raw
         code or the literal "unknown" sentinel. `resolve_subject_labels` /
         `display_subject` resolve via curriculum_units + content_subject_versions.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.core.subjects import display_subject, resolve_subject_labels
from tests.helpers.token_factory import make_student_token

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
        f"auth0|test-{student_id.replace('-', '')[:20]}",
        f"Test Student {student_id[:6]}",
        f"test-{student_id[:6]}@test.invalid",
    )


async def _start_session(client: AsyncClient, token: str) -> dict:
    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": "G8-MATH-001", "curriculum_id": "default-2026-g8"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── #460 — score clamp ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_session_clamps_score_above_total(client, db_conn):
    """A score greater than total_questions is clamped to total (no 8/5=160%)."""
    student_id = str(uuid.uuid4())
    await _insert_student(client, student_id)
    token = make_student_token(student_id=student_id, grade=8)
    session = await _start_session(client, token)

    # end_session dispatches streak/view-refresh Celery tasks via send_task.
    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={"score": 8, "total_questions": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == 5  # clamped from 8
    assert data["total_questions"] == 5
    assert data["passed"] is True


@pytest.mark.asyncio
async def test_end_session_valid_score_unchanged(client, db_conn):
    """A normal score passes through untouched and computes passed correctly."""
    student_id = str(uuid.uuid4())
    await _insert_student(client, student_id)
    token = make_student_token(student_id=student_id, grade=8)
    session = await _start_session(client, token)

    with patch("src.auth.tasks.celery_app.send_task", return_value=None):
        r = await client.post(
            f"/api/v1/progress/session/{session['session_id']}/end",
            json={"score": 2, "total_questions": 8},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == 2
    assert data["total_questions"] == 8
    assert data["passed"] is False  # 2/8 = 25% < 60%


# ── #462 — subject label resolution ───────────────────────────────────────────


async def _seed_curriculum(db_conn, curriculum_id: str, subject_code: str, subject_name: str | None):
    await db_conn.execute(
        "INSERT INTO curricula (curriculum_id, grade, year, name) VALUES ($1, 8, 2026, $2)",
        curriculum_id,
        f"Test {curriculum_id}",
    )
    await db_conn.execute(
        "INSERT INTO curriculum_units (unit_id, curriculum_id, subject, title, unit_name) "
        "VALUES ($1, $2, $3, $4, $4)",
        f"{subject_code}-005",
        curriculum_id,
        subject_code,
        "Mechanical Systems",
    )
    await db_conn.execute(
        """
        INSERT INTO content_subject_versions (curriculum_id, subject, subject_name, version_number, status)
        VALUES ($1, $2, $3, 1, 'published')
        """,
        curriculum_id,
        subject_code,
        subject_name,
    )


@pytest.mark.asyncio
async def test_resolve_subject_labels_prefers_subject_name(db_conn):
    """Display name from content_subject_versions wins over the raw code."""
    cid = f"test-cur-{uuid.uuid4().hex[:8]}"
    await _seed_curriculum(db_conn, cid, "G8-SCI", "Natural Sciences")

    labels = await resolve_subject_labels(db_conn, ["G8-SCI-005"])
    assert labels["G8-SCI-005"] == "Natural Sciences"


@pytest.mark.asyncio
async def test_resolve_subject_labels_falls_back_to_code(db_conn):
    """With no subject_name, the curriculum_units code is used (never 'unknown')."""
    cid = f"test-cur-{uuid.uuid4().hex[:8]}"
    await _seed_curriculum(db_conn, cid, "G8-MATH", None)

    labels = await resolve_subject_labels(db_conn, ["G8-MATH-005"])
    assert labels["G8-MATH-005"] == "G8-MATH"


@pytest.mark.asyncio
async def test_resolve_subject_labels_empty_input(db_conn):
    assert await resolve_subject_labels(db_conn, []) == {}


def test_display_subject_resolution_order():
    """Pure-function fallback chain: map → stored (non-sentinel) → unit_id → 'Unknown'."""
    label_map = {"u1": "Physics"}
    # curriculum label wins even when the stored value is the 'unknown' sentinel
    assert display_subject(label_map, "u1", "unknown") == "Physics"
    # no map entry → fall back to a meaningful stored code
    assert display_subject({}, "u2", "G8-SCI") == "G8-SCI"
    # no map entry and stored is the sentinel, unit_id not parseable → 'Unknown'
    assert display_subject({}, "u2", "unknown") == "Unknown"
    assert display_subject({}, "u2", "UNKNOWN") == "Unknown"
    assert display_subject({}, "u2", None) == "Unknown"


def test_display_subject_falls_back_to_unit_id_prefix():
    """When the curriculum label is missing and the stored subject is the
    'unknown' sentinel, a real subject is derived from the unit_id prefix so
    the breakdown chart never collapses to a single 'Unknown' bar (#473)."""
    from src.core.subjects import subject_from_unit_id

    assert display_subject({}, "G8-SCI-001", "unknown") == "Science"
    assert display_subject({}, "G11-PHYS-002", None) == "Physics"
    assert display_subject({}, "G12-MATH-005", "unknown") == "Mathematics"
    # Unrecognised code or non-matching id → still 'Unknown'.
    assert display_subject({}, "G9-ZZZ-001", "unknown") == "Unknown"

    # Direct helper coverage.
    assert subject_from_unit_id("G8-SCI-001") == "Science"
    assert subject_from_unit_id("not-a-unit-id") is None
    assert subject_from_unit_id(None) is None
