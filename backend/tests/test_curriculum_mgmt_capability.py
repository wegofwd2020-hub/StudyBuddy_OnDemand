"""
tests/test_curriculum_mgmt_capability.py

Issue #358 — curriculum_mgmt additive capability.

Covers:
  has_capability / has_any_curriculum_capability helpers (unit, no DB)
  PUT/GET /api/v1/schools/{id}/teachers/{tid}/capabilities  — assign / read
  Three-tier guards on the curriculum endpoints:
    Tier 0 view       — any curriculum capability (or school_admin)
    Tier 1 commission — curriculum.commission | umbrella | school_admin
    Tier 2 review     — curriculum.review     | umbrella | school_admin
  Gate isolation (commission ≠ review) and the read/act split.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.core.permissions import has_any_curriculum_capability, has_capability
from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"

_VALID_DEFN = {
    "name": "Grade 8 STEM — Semester 1",
    "grade": 8,
    "languages": ["en"],
    "subjects": [
        {"subject_label": "Mathematics", "units": [{"title": "Quadratics"}]},
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _register_school(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _provision_teacher(
    client: AsyncClient, school_id: str, admin_token: str, email: str
) -> str:
    with patch("src.email.service.send_welcome_teacher_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Test Teacher", "email": email},
            headers=_auth(admin_token),
        )
    assert r.status_code == 201, r.text
    return r.json()["teacher_id"]


async def _grant(client, school_id, admin_token, tid, caps) -> None:
    r = await client.put(
        f"/api/v1/schools/{school_id}/teachers/{tid}/capabilities",
        json={"capabilities": caps},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200, r.text


async def _submit_defn(client, school_id, admin_token) -> str:
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=_VALID_DEFN,
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["definition_id"]


# ── has_capability unit tests (no DB) ─────────────────────────────────────────


def test_admin_has_all_capabilities():
    assert has_capability({"role": "school_admin"}, "curriculum.commission") is True
    assert has_capability({"role": "school_admin"}, "curriculum.review") is True


def test_exact_grant_is_gate_isolated():
    p = {"role": "teacher", "capabilities": ["curriculum.commission"]}
    assert has_capability(p, "curriculum.commission") is True
    assert has_capability(p, "curriculum.review") is False


def test_umbrella_covers_both_gates():
    p = {"role": "teacher", "capabilities": ["curriculum_mgmt"]}
    assert has_capability(p, "curriculum.commission") is True
    assert has_capability(p, "curriculum.review") is True


def test_missing_capabilities_key_defaults_false():
    assert has_capability({"role": "teacher"}, "curriculum.review") is False


def test_any_curriculum_capability():
    assert has_any_curriculum_capability({"role": "teacher", "capabilities": ["curriculum.review"]})
    assert has_any_curriculum_capability({"role": "school_admin"})
    assert not has_any_curriculum_capability({"role": "teacher", "capabilities": []})


# ── Assign endpoint ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_grants_and_reads_back(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap S1", "cap1@example.com")
    sid, admin = school["school_id"], school["access_token"]
    tid = await _provision_teacher(client, sid, admin, "t1@example.com")

    r = await client.put(
        f"/api/v1/schools/{sid}/teachers/{tid}/capabilities",
        json={"capabilities": ["curriculum.commission"]},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text
    assert r.json()["capabilities"] == ["curriculum.commission"]

    r = await client.get(
        f"/api/v1/schools/{sid}/teachers/{tid}/capabilities", headers=_auth(admin)
    )
    assert r.json()["capabilities"] == ["curriculum.commission"]


@pytest.mark.asyncio
async def test_revocation(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap S2", "cap2@example.com")
    sid, admin = school["school_id"], school["access_token"]
    tid = await _provision_teacher(client, sid, admin, "t2@example.com")

    await _grant(client, sid, admin, tid, ["curriculum_mgmt"])
    await _grant(client, sid, admin, tid, [])  # revoke

    r = await client.get(
        f"/api/v1/schools/{sid}/teachers/{tid}/capabilities", headers=_auth(admin)
    )
    assert r.json()["capabilities"] == []


@pytest.mark.asyncio
async def test_assign_requires_admin(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap S3", "cap3@example.com")
    sid = school["school_id"]
    cm = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-000000000099",
        school_id=sid,
        role="teacher",
        capabilities=["curriculum_mgmt"],
    )
    r = await client.put(
        f"/api/v1/schools/{sid}/teachers/d2000000-0000-0000-0000-000000000098/capabilities",
        json={"capabilities": ["curriculum_mgmt"]},
        headers=_auth(cm),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cross_school_grant_forbidden(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap S4", "cap4@example.com")
    sid = school["school_id"]
    other_admin = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-000000000097",
        school_id="d3000000-0000-0000-0000-0000000000ff",
        role="school_admin",
    )
    r = await client.put(
        f"/api/v1/schools/{sid}/teachers/d2000000-0000-0000-0000-000000000096/capabilities",
        json={"capabilities": ["curriculum_mgmt"]},
        headers=_auth(other_admin),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("caps", [["bogus_cap"], ["curriculum_mgmt", "bogus"]])
async def test_unknown_capability_rejected(client: AsyncClient, db_conn, caps) -> None:
    school = await _register_school(client, f"Cap S5 {caps}", f"cap5{len(caps[0])}@example.com")
    sid, admin = school["school_id"], school["access_token"]
    tid = await _provision_teacher(client, sid, admin, f"t5{len(caps[0])}@example.com")
    r = await client.put(
        f"/api/v1/schools/{sid}/teachers/{tid}/capabilities",
        json={"capabilities": caps},
        headers=_auth(admin),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unknown_teacher_404(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap S6", "cap6@example.com")
    sid, admin = school["school_id"], school["access_token"]
    r = await client.put(
        f"/api/v1/schools/{sid}/teachers/d2000000-0000-0000-0000-0000000000aa/capabilities",
        json={"capabilities": ["curriculum_mgmt"]},
        headers=_auth(admin),
    )
    assert r.status_code == 404


# ── Gate 1 (commission) guard on approve_definition ───────────────────────────


@pytest.mark.asyncio
async def test_commission_teacher_can_approve_definition(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap G1", "g1@example.com")
    sid, admin = school["school_id"], school["access_token"]
    tid = await _provision_teacher(client, sid, admin, "g1t@example.com")
    await _grant(client, sid, admin, tid, ["curriculum.commission"])
    defn_id = await _submit_defn(client, sid, admin)

    tok = make_teacher_token(
        teacher_id=tid, school_id=sid, role="teacher", capabilities=["curriculum.commission"]
    )
    r = await client.post(
        f"/api/v1/schools/{sid}/curriculum/definitions/{defn_id}/approve", headers=_auth(tok)
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_plain_teacher_cannot_approve_definition(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap G2", "g2@example.com")
    sid, admin = school["school_id"], school["access_token"]
    defn_id = await _submit_defn(client, sid, admin)
    tok = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-0000000000b1", school_id=sid, role="teacher"
    )
    r = await client.post(
        f"/api/v1/schools/{sid}/curriculum/definitions/{defn_id}/approve", headers=_auth(tok)
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_implicit_approve(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap G3", "g3@example.com")
    sid, admin = school["school_id"], school["access_token"]
    defn_id = await _submit_defn(client, sid, admin)
    r = await client.post(
        f"/api/v1/schools/{sid}/curriculum/definitions/{defn_id}/approve", headers=_auth(admin)
    )
    assert r.status_code == 200, r.text


# ── Gate isolation + read/act split ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_review_grant_cannot_clear_commission_gate(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap GI", "gi@example.com")
    sid, admin = school["school_id"], school["access_token"]
    defn_id = await _submit_defn(client, sid, admin)
    tok = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-0000000000c1",
        school_id=sid,
        role="teacher",
        capabilities=["curriculum.review"],
    )
    r = await client.post(
        f"/api/v1/schools/{sid}/curriculum/definitions/{defn_id}/approve", headers=_auth(tok)
    )
    assert r.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cap", ["curriculum.commission", "curriculum.review", "curriculum_mgmt"]
)
async def test_any_capability_can_view_review_queue(client: AsyncClient, db_conn, cap) -> None:
    school = await _register_school(client, f"Cap V {cap}", f"v{cap[-4:]}@example.com")
    sid = school["school_id"]
    tok = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-0000000000d1",
        school_id=sid,
        role="teacher",
        capabilities=[cap],
    )
    r = await client.get(f"/api/v1/schools/{sid}/content/review-queue", headers=_auth(tok))
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_plain_teacher_cannot_view_review_queue(client: AsyncClient, db_conn) -> None:
    school = await _register_school(client, "Cap VP", "vp@example.com")
    sid = school["school_id"]
    tok = make_teacher_token(
        teacher_id="d2000000-0000-0000-0000-0000000000e1", school_id=sid, role="teacher"
    )
    r = await client.get(f"/api/v1/schools/{sid}/content/review-queue", headers=_auth(tok))
    assert r.status_code == 403
