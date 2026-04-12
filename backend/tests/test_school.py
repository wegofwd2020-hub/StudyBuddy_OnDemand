"""
tests/test_school.py

Tests for Phase 8 school endpoints:
  POST /api/v1/schools/register
  GET  /api/v1/schools/{school_id}
  POST /api/v1/schools/{school_id}/teachers/invite
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

# Shared test password satisfying the 12-char minimum.
_PW = "SecureTestPwd1!"


def _reg(name: str, email: str, country: str = "CA") -> dict:
    """Build a school registration payload with the required password field."""
    return {"school_name": name, "contact_email": email, "country": country, "password": _PW}


# ── POST /schools/register ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_school_returns_201(client: AsyncClient):
    """Successful school registration returns 201 with access_token."""
    r = await client.post("/api/v1/schools/register", json=_reg("Test Academy", "admin@testacademy.example.com", "US"))
    assert r.status_code == 201, r.text
    data = r.json()
    assert "school_id" in data
    assert "teacher_id" in data
    assert "access_token" in data
    assert data["role"] == "school_admin"


@pytest.mark.asyncio
async def test_register_school_duplicate_email_returns_409(client: AsyncClient):
    """Registering the same email twice returns 409 Conflict."""
    payload = _reg("Dup Academy", "dup@testacademy.example.com")
    r1 = await client.post("/api/v1/schools/register", json=payload)
    assert r1.status_code == 201, r1.text

    r2 = await client.post("/api/v1/schools/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"] == "conflict"


@pytest.mark.asyncio
async def test_register_school_missing_name_returns_422(client: AsyncClient):
    """Missing required field returns 422 Unprocessable Entity."""
    r = await client.post("/api/v1/schools/register", json={"contact_email": "x@x.com", "password": _PW})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_school_short_password_returns_422(client: AsyncClient):
    """Password shorter than 12 characters returns 422."""
    payload = {"school_name": "Weak Academy", "contact_email": "weak@example.com", "country": "CA", "password": "short"}
    r = await client.post("/api/v1/schools/register", json=payload)
    assert r.status_code == 422


# ── GET /schools/{school_id} ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_school_profile_requires_auth(client: AsyncClient):
    """GET school profile without JWT returns 401."""
    r = await client.get("/api/v1/schools/some-school-id")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_school_profile_returns_school(client: AsyncClient):
    """School admin can fetch their own school profile."""
    reg = await client.post("/api/v1/schools/register", json=_reg("Profile Academy", "profile@example.com", "GB"))
    assert reg.status_code == 201, reg.text
    data = reg.json()
    school_id = data["school_id"]
    token = data["access_token"]

    r = await client.get(
        f"/api/v1/schools/{school_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    profile = r.json()
    assert profile["school_id"] == school_id
    assert "name" in profile
    assert "contact_email" in profile
    assert "enrolment_code" in profile


@pytest.mark.asyncio
async def test_get_school_profile_wrong_school_returns_404(client: AsyncClient):
    """Teacher cannot access a school they do not belong to."""
    reg1 = await client.post("/api/v1/schools/register", json=_reg("School A", "schoola@example.com", "US"))
    reg2 = await client.post("/api/v1/schools/register", json=_reg("School B", "schoolb@example.com", "US"))
    assert reg1.status_code == 201 and reg2.status_code == 201

    school_b_id = reg2.json()["school_id"]
    token_a = reg1.json()["access_token"]

    r = await client.get(
        f"/api/v1/schools/{school_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 404


# ── POST /schools/{school_id}/teachers/invite ─────────────────────────────────

@pytest.mark.asyncio
async def test_invite_teacher_school_admin_succeeds(client: AsyncClient):
    """school_admin can invite a teacher to their school."""
    reg = await client.post("/api/v1/schools/register", json=_reg("Invite Academy", "invite-admin@example.com", "AU"))
    assert reg.status_code == 201, reg.text
    data = reg.json()
    school_id = data["school_id"]
    token = data["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json={"name": "Jane Smith", "email": "jane@inviteacademy.example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    result = r.json()
    assert "teacher_id" in result
    assert result["email"] == "jane@inviteacademy.example.com"
    assert result["role"] == "teacher"


@pytest.mark.asyncio
async def test_invite_teacher_non_admin_returns_403(client: AsyncClient):
    """A regular teacher (not school_admin) cannot invite new teachers."""
    reg = await client.post("/api/v1/schools/register", json=_reg("Perm Academy", "perm-admin@example.com", "US"))
    assert reg.status_code == 201
    school_id = reg.json()["school_id"]

    teacher_token = make_teacher_token(school_id=school_id, role="teacher")
    r = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json={"name": "Bob", "email": "bob@perm.example.com"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_invite_teacher_wrong_school_returns_403(client: AsyncClient):
    """school_admin cannot invite teachers to a different school."""
    reg = await client.post("/api/v1/schools/register", json=_reg("Cross Academy", "cross@example.com", "US"))
    assert reg.status_code == 201
    data = reg.json()
    school_id = data["school_id"]
    token = data["access_token"]

    different_school_id = "00000000-0000-0000-0000-000000000001"
    r = await client.post(
        f"/api/v1/schools/{different_school_id}/teachers/invite",
        json={"name": "Eve", "email": "eve@cross.example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_invite_teacher_duplicate_email_returns_409(client: AsyncClient):
    """Inviting the same email twice returns 409 Conflict."""
    reg = await client.post("/api/v1/schools/register", json=_reg("Dup Invite Academy", "dup-invite-admin@example.com", "US"))
    assert reg.status_code == 201
    data = reg.json()
    school_id = data["school_id"]
    token = data["access_token"]

    invite_payload = {"name": "Same Teacher", "email": "same@dupinvite.example.com"}
    r1 = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json=invite_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json=invite_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_invite_teacher_requires_auth(client: AsyncClient):
    """Invite endpoint without JWT returns 401."""
    r = await client.post(
        "/api/v1/schools/some-school-id/teachers/invite",
        json={"name": "X", "email": "x@x.com"},
    )
    assert r.status_code == 401


# ── G1: schools.contact_email uniqueness (ADR-001) ───────────────────────────

@pytest.mark.asyncio
async def test_register_school_same_contact_email_returns_409(client: AsyncClient):
    """
    Two schools cannot share the same contact_email.
    The constraint fires on the schools INSERT now (G1), giving a clear 409
    before the teachers INSERT is even attempted.
    """
    payload = _reg("First School", "shared@sameemail.example.com", "US")
    r1 = await client.post("/api/v1/schools/register", json=payload)
    assert r1.status_code == 201, r1.text

    payload2 = {**payload, "school_name": "Second School"}
    r2 = await client.post("/api/v1/schools/register", json=payload2)
    assert r2.status_code == 409
    assert r2.json()["error"] == "conflict"


# ── G2: teacher school_id constraint (ADR-001) ───────────────────────────────

@pytest.mark.asyncio
async def test_invite_teacher_always_has_school_id(client: AsyncClient):
    """
    Every invited teacher gets the school's school_id — the G2 CHECK constraint
    (school_id IS NOT NULL OR auth_provider = 'demo') is satisfied automatically
    because invite_teacher() always writes the school_id.
    Verifies the teacher appears in the school's teacher list with the correct school.
    """
    reg = await client.post("/api/v1/schools/register", json=_reg("G2 Academy", "g2-admin@example.com"))
    assert reg.status_code == 201, reg.text
    data = reg.json()
    school_id = data["school_id"]
    token = data["access_token"]

    inv = await client.post(
        f"/api/v1/schools/{school_id}/teachers/invite",
        json={"name": "Affiliated Teacher", "email": "affiliated@g2.example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inv.status_code == 201, inv.text

    roster_r = await client.get(
        f"/api/v1/schools/{school_id}/teachers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert roster_r.status_code == 200, roster_r.text
    emails = [t["email"] for t in roster_r.json()["teachers"]]
    assert "affiliated@g2.example.com" in emails
