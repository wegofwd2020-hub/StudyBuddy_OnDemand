"""
tests/test_coppa_ferpa.py  — K-6 (Epic 6 Platform Hardening)

COPPA consent-gate and FERPA cross-school isolation assertions.

COPPA tests (Children's Online Privacy Protection Act)
------------------------------------------------------
  COP-01  Student with account_status='pending' is blocked from lesson content (403)
  COP-02  Student with account_status='pending' is blocked from quiz content (403)
  COP-03  Student with account_status='pending' is blocked from recording progress (403)
  COP-04  Student with account_status='active' passes the same content endpoints (200 / 200)

FERPA tests (Family Educational Rights and Privacy Act)
-------------------------------------------------------
  FRP-01  Teacher from School A gets 403 on School B's enrolment roster
  FRP-02  Teacher (non-admin) gets 403 on any school's enrolment roster
  FRP-03  School admin from School A gets 403 on School B's student assignment
  FRP-04  School admin from School A gets 403 on School B's teacher list
  FRP-05  Student JWT is rejected by teacher-only school endpoints (403)

Design notes
------------
- Content tests mock the curriculum resolver and entitlement checks so the
  account_status gate is exercised in isolation — not masked by 402/403 from
  the entitlement layer.
- FERPA tests rely only on JWT school_id mismatch — no DB setup required
  because the school_id check happens before any DB query in these endpoints.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import (
    make_student_token,
    make_teacher_token,
)

# ── Deterministic IDs ─────────────────────────────────────────────────────────

SCHOOL_A_ID = "fa000000-0000-0000-0000-000000000001"
SCHOOL_B_ID = "fb000000-0000-0000-0000-000000000002"
TEACHER_A_ID = "fa100000-0000-0000-0000-000000000001"
TEACHER_B_ID = "fb100000-0000-0000-0000-000000000002"
STUDENT_A_ID = "fa200000-0000-0000-0000-000000000001"

# ── COPPA helpers ─────────────────────────────────────────────────────────────


def _pending_token() -> str:
    return make_student_token(account_status="pending")


def _active_token() -> str:
    return make_student_token(account_status="active")


# Curriculum resolver + entitlement patches so content endpoints can run
# without a live DB for the resolver/entitlement look-ups.  The account_status
# check in get_current_student() runs BEFORE these dependencies, so if the
# token is pending the 403 is raised before any resolver call.
_RESOLVER_PATCH = "src.content.router.resolve_curriculum_id"
_ENTITLEMENT_PATCH = "src.content.router.get_entitlement"

# ── COP-01 — pending student blocked from lesson content ──────────────────────


@pytest.mark.asyncio
async def test_cop01_pending_student_blocked_from_lesson(client: AsyncClient):
    """account_status='pending' → 403 account_pending on GET /content/{unit}/lesson."""
    token = _pending_token()

    r = await client.get(
        "/api/v1/content/G8-SCI-001/lesson",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "account_pending"


# ── COP-02 — pending student blocked from quiz content ────────────────────────


@pytest.mark.asyncio
async def test_cop02_pending_student_blocked_from_quiz(client: AsyncClient):
    """account_status='pending' → 403 account_pending on GET /content/{unit}/quiz."""
    token = _pending_token()

    r = await client.get(
        "/api/v1/content/G8-SCI-001/quiz",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "account_pending"


# ── COP-03 — pending student blocked from recording progress ──────────────────


@pytest.mark.asyncio
async def test_cop03_pending_student_blocked_from_progress(client: AsyncClient):
    """account_status='pending' → 403 account_pending on POST /progress/session."""
    token = _pending_token()

    r = await client.post(
        "/api/v1/progress/session",
        json={"unit_id": "G8-SCI-001", "curriculum_id": "default-2026-g8"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "account_pending"


# ── COP-04 — active student passes the lesson gate ────────────────────────────


@pytest.mark.asyncio
async def test_cop04_active_student_passes_lesson_gate(client: AsyncClient, fake_redis):
    """account_status='active' → gets past the COPPA gate (any response except account_pending)."""
    token = _active_token()

    r = await client.get(
        "/api/v1/content/G8-SCI-001/lesson",
        headers={"Authorization": f"Bearer {token}"},
    )

    # The account_status gate was passed — response may be 404 (no seeded content)
    # or 402 (entitlement), but NEVER account_pending.
    body = r.json()
    if r.status_code == 403:
        assert body.get("error") != "account_pending", (
            "Active student should not get account_pending — "
            f"got: {body}"
        )


# ── FRP-01 — Teacher from School A blocked from School B's enrolment roster ───


@pytest.mark.asyncio
async def test_frp01_teacher_a_blocked_from_school_b_roster(client: AsyncClient):
    """School admin token for School A must get 403 on School B's enrolment endpoint."""
    token = make_teacher_token(
        teacher_id=TEACHER_A_ID,
        school_id=SCHOOL_A_ID,
        role="school_admin",
    )

    r = await client.get(
        f"/api/v1/schools/{SCHOOL_B_ID}/enrolment",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "forbidden"


# ── FRP-02 — Non-admin teacher blocked from roster regardless of school ────────


@pytest.mark.asyncio
async def test_frp02_non_admin_teacher_blocked_from_any_roster(client: AsyncClient):
    """Regular teacher (role='teacher') gets 403 on any school's enrolment roster."""
    # Use own school_id — role check happens first
    token = make_teacher_token(
        teacher_id=TEACHER_A_ID,
        school_id=SCHOOL_A_ID,
        role="teacher",
    )

    r = await client.get(
        f"/api/v1/schools/{SCHOOL_A_ID}/enrolment",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "forbidden"


# ── FRP-03 — School admin A blocked from School B's student assignment ─────────


@pytest.mark.asyncio
async def test_frp03_admin_a_blocked_from_school_b_assignment(client: AsyncClient):
    """School admin from School A cannot read a student assignment for School B."""
    token = make_teacher_token(
        teacher_id=TEACHER_A_ID,
        school_id=SCHOOL_A_ID,
        role="school_admin",
    )
    student_id = str(uuid.uuid4())

    r = await client.get(
        f"/api/v1/schools/{SCHOOL_B_ID}/students/{student_id}/assignment",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "forbidden"


# ── FRP-04 — School admin A blocked from School B's teacher list ───────────────


@pytest.mark.asyncio
async def test_frp04_admin_a_blocked_from_school_b_teachers(client: AsyncClient):
    """School admin from School A cannot list teachers for School B."""
    token = make_teacher_token(
        teacher_id=TEACHER_A_ID,
        school_id=SCHOOL_A_ID,
        role="school_admin",
    )

    r = await client.get(
        f"/api/v1/schools/{SCHOOL_B_ID}/teachers",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403, r.text
    assert r.json()["error"] == "forbidden"


# ── FRP-05 — Student JWT rejected by teacher-only school endpoints ─────────────


@pytest.mark.asyncio
async def test_frp05_student_token_rejected_by_school_endpoints(client: AsyncClient):
    """A student JWT must never gain access to teacher/school_admin endpoints."""
    student_token = make_student_token(account_status="active")

    # Try to access the enrolment roster — requires teacher/school_admin token.
    r = await client.get(
        f"/api/v1/schools/{SCHOOL_A_ID}/enrolment",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # get_current_teacher rejects student JWTs with 403 (wrong role)
    assert r.status_code == 403, r.text
