"""
tests/test_phase_d_definitions.py

Phase D — Curriculum Definition lifecycle tests.

Coverage:
  POST   /api/v1/schools/{id}/curriculum/definitions                          — submit
  GET    /api/v1/schools/{id}/curriculum/definitions                          — list (admin / teacher)
  GET    /api/v1/schools/{id}/curriculum/definitions?status=pending_approval  — filter
  GET    /api/v1/schools/{id}/curriculum/definitions/{def_id}                 — detail
  POST   /api/v1/schools/{id}/curriculum/definitions/{def_id}/approve         — approve
  POST   /api/v1/schools/{id}/curriculum/definitions/{def_id}/reject          — reject
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token

_PW = "SecureTestPwd1!"

_VALID_BODY = {
    "name": "Grade 8 STEM — Semester 1",
    "grade": 8,
    "languages": ["en", "fr"],
    "subjects": [
        {
            "subject_label": "Mathematics",
            "units": [{"title": "Quadratic Equations"}, {"title": "Polynomials"}],
        },
        {
            "subject_label": "Science",
            "units": [{"title": "Cells and Genetics"}],
        },
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────────


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
) -> tuple[str, str]:
    """Provision a teacher and return (teacher_id, teacher_token)."""
    with patch("src.email.service.send_welcome_teacher_email", new=AsyncMock()):
        r = await client.post(
            f"/api/v1/schools/{school_id}/teachers",
            json={"name": "Test Teacher", "email": email},
            headers=_auth(admin_token),
        )
    assert r.status_code == 201, r.text
    teacher_id = r.json()["teacher_id"]
    # Mint a JWT for this teacher directly (provision response has no token)
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role="teacher")
    return teacher_id, token


async def _submit(
    client: AsyncClient, school_id: str, token: str, body: dict | None = None
) -> dict:
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=body or _VALID_BODY,
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Submit ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_definition_admin(client: AsyncClient, db_conn) -> None:
    """School admin can submit a definition; starts in pending_approval."""
    school = await _register_school(client, "Def School Admin", "def-admin@example.com")
    school_id, token = school["school_id"], school["access_token"]

    defn = await _submit(client, school_id, token)

    assert defn["status"] == "pending_approval"
    assert defn["name"] == _VALID_BODY["name"]
    assert defn["grade"] == 8
    assert defn["languages"] == ["en", "fr"]
    assert len(defn["subjects"]) == 2
    assert defn["rejection_reason"] is None
    assert defn["reviewed_by"] is None


@pytest.mark.asyncio
async def test_submit_definition_teacher(client: AsyncClient, db_conn) -> None:
    """Regular teacher can also submit a definition."""
    school = await _register_school(client, "Def School Teacher", "def-teacher@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, teacher_token = await _provision_teacher(
        client, school_id, admin_token, "teacher-defn@example.com"
    )

    defn = await _submit(client, school_id, teacher_token)
    assert defn["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_submit_definition_wrong_school(client: AsyncClient, db_conn) -> None:
    """Teacher cannot submit to a different school."""
    school1 = await _register_school(client, "Def School A", "def-school-a@example.com")
    school2 = await _register_school(client, "Def School B", "def-school-b@example.com")

    token = make_teacher_token(
        teacher_id=str(uuid.uuid4()),
        school_id=school1["school_id"],
        role="teacher",
    )

    r = await client.post(
        f"/api/v1/schools/{school2['school_id']}/curriculum/definitions",
        json=_VALID_BODY,
        headers=_auth(token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_submit_definition_invalid_grade(client: AsyncClient, db_conn) -> None:
    """Grade out of 1–12 is rejected by schema validation."""
    school = await _register_school(client, "Def School Grade", "def-grade@example.com")
    school_id, token = school["school_id"], school["access_token"]

    body = {**_VALID_BODY, "grade": 0}
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=body,
        headers=_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_definition_empty_subjects(client: AsyncClient, db_conn) -> None:
    """Definition with no subjects is rejected."""
    school = await _register_school(client, "Def School Empty", "def-empty@example.com")
    school_id, token = school["school_id"], school["access_token"]

    body = {**_VALID_BODY, "subjects": []}
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=body,
        headers=_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_definition_no_units(client: AsyncClient, db_conn) -> None:
    """Subject with no units is rejected."""
    school = await _register_school(client, "Def School NoUnits", "def-nounits@example.com")
    school_id, token = school["school_id"], school["access_token"]

    body = {
        **_VALID_BODY,
        "subjects": [{"subject_label": "Math", "units": []}],
    }
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=body,
        headers=_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_definition_invalid_language(client: AsyncClient, db_conn) -> None:
    """Unsupported language code is rejected."""
    school = await _register_school(client, "Def School Lang", "def-lang@example.com")
    school_id, token = school["school_id"], school["access_token"]

    body = {**_VALID_BODY, "languages": ["en", "de"]}
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=body,
        headers=_auth(token),
    )
    assert r.status_code == 422


# ── List ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_definitions_admin_sees_all(client: AsyncClient, db_conn) -> None:
    """Admin can see all definitions, including those submitted by teachers."""
    school = await _register_school(client, "Def List School", "def-list@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, teacher_token = await _provision_teacher(
        client, school_id, admin_token, "teacher-list@example.com"
    )

    # Teacher submits one
    await _submit(client, school_id, teacher_token)
    # Admin submits one
    await _submit(client, school_id, admin_token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_list_definitions_teacher_sees_own(client: AsyncClient, db_conn) -> None:
    """Regular teacher only sees their own definitions."""
    school = await _register_school(client, "Def Own School", "def-own@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, teacher_token = await _provision_teacher(
        client, school_id, admin_token, "teacher-own@example.com"
    )

    # Teacher submits one; admin also submits one
    await _submit(client, school_id, teacher_token)
    await _submit(client, school_id, admin_token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        headers=_auth(teacher_token),
    )
    assert r.status_code == 200
    data = r.json()
    # Teacher should only see their own submission, not the admin's
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_definitions_status_filter(client: AsyncClient, db_conn) -> None:
    """?status= filter returns only matching definitions."""
    school = await _register_school(client, "Def Filter School", "def-filter@example.com")
    school_id, token = school["school_id"], school["access_token"]

    await _submit(client, school_id, token)

    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions?status=pending_approval",
        headers=_auth(token),
    )
    assert r.status_code == 200
    data = r.json()
    for d in data["definitions"]:
        assert d["status"] == "pending_approval"

    r2 = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions?status=approved",
        headers=_auth(token),
    )
    assert r2.status_code == 200
    # No approved ones yet — this school only has pending submissions
    # (other schools' rows are isolated by RLS, so 0 or more from this school)
    for d in r2.json()["definitions"]:
        assert d["status"] == "approved"


# ── Detail ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_definition_detail(client: AsyncClient, db_conn) -> None:
    """Detail endpoint returns the full definition including subjects."""
    school = await _register_school(client, "Def Detail School", "def-detail@example.com")
    school_id, token = school["school_id"], school["access_token"]

    submitted = await _submit(client, school_id, token)
    definition_id = submitted["definition_id"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}",
        headers=_auth(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["definition_id"] == definition_id
    assert len(data["subjects"]) == 2
    subj_labels = {s["subject_label"] for s in data["subjects"]}
    assert "Mathematics" in subj_labels


@pytest.mark.asyncio
async def test_get_definition_not_found(client: AsyncClient, db_conn) -> None:
    """404 for a definition_id that doesn't exist."""
    school = await _register_school(client, "Def 404 School", "def-404@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{uuid.uuid4()}",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_definition_teacher_cannot_see_others(client: AsyncClient, db_conn) -> None:
    """A teacher cannot fetch another teacher's definition."""
    school = await _register_school(client, "Def Priv School", "def-priv@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, t1_token = await _provision_teacher(client, school_id, admin_token, "t1-priv@example.com")
    _, t2_token = await _provision_teacher(client, school_id, admin_token, "t2-priv@example.com")

    # Teacher 1 submits
    submitted = await _submit(client, school_id, t1_token)
    definition_id = submitted["definition_id"]

    # Teacher 2 tries to read it
    r = await client.get(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}",
        headers=_auth(t2_token),
    )
    assert r.status_code == 403


# ── Approve ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_definition(client: AsyncClient, db_conn) -> None:
    """School admin can approve a pending definition."""
    school = await _register_school(client, "Def Approve School", "def-approve@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    submitted = await _submit(client, school_id, admin_token)
    definition_id = submitted["definition_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] is not None
    assert data["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_approve_definition_non_admin_forbidden(client: AsyncClient, db_conn) -> None:
    """Regular teacher cannot approve a definition."""
    school = await _register_school(client, "Def Approve Forbidden", "def-appfb@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, teacher_token = await _provision_teacher(
        client, school_id, admin_token, "teacher-appfb@example.com"
    )
    submitted = await _submit(client, school_id, admin_token)
    definition_id = submitted["definition_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(teacher_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_approve_already_approved_returns_409(client: AsyncClient, db_conn) -> None:
    """Approving an already-approved definition returns 409."""
    school = await _register_school(client, "Def Double Approve", "def-dbl@example.com")
    school_id, token = school["school_id"], school["access_token"]

    submitted = await _submit(client, school_id, token)
    definition_id = submitted["definition_id"]

    # First approval succeeds
    r1 = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(token),
    )
    assert r1.status_code == 200

    # Second approval on same definition → 409
    r2 = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(token),
    )
    assert r2.status_code == 409


# ── Reject ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_definition(client: AsyncClient, db_conn) -> None:
    """School admin can reject a pending definition with a reason."""
    school = await _register_school(client, "Def Reject School", "def-reject@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    submitted = await _submit(client, school_id, admin_token)
    definition_id = submitted["definition_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/reject",
        json={"reason": "Units are too broad — please narrow each unit to one topic."},
        headers=_auth(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert "broad" in data["rejection_reason"]
    assert data["reviewed_by"] is not None


@pytest.mark.asyncio
async def test_reject_definition_non_admin_forbidden(client: AsyncClient, db_conn) -> None:
    """Regular teacher cannot reject a definition."""
    school = await _register_school(client, "Def Reject Forbidden", "def-rejfb@example.com")
    school_id, admin_token = school["school_id"], school["access_token"]

    _, teacher_token = await _provision_teacher(
        client, school_id, admin_token, "teacher-rejfb@example.com"
    )
    submitted = await _submit(client, school_id, admin_token)
    definition_id = submitted["definition_id"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/reject",
        json={"reason": "Not approved."},
        headers=_auth(teacher_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reject_approved_definition_returns_409(client: AsyncClient, db_conn) -> None:
    """Cannot reject an already-approved definition."""
    school = await _register_school(client, "Def Reject Approved", "def-rejapp@example.com")
    school_id, token = school["school_id"], school["access_token"]

    submitted = await _submit(client, school_id, token)
    definition_id = submitted["definition_id"]

    # Approve first
    await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(token),
    )

    # Now try to reject → 409
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/reject",
        json={"reason": "Changed my mind."},
        headers=_auth(token),
    )
    assert r.status_code == 409
