"""
tests/test_export_entitlement_scope.py

The CSV export honours the caller's entitlement, and a download cannot cross a
school boundary.

Found while scoping #772 ("group CSV export by Grade/Steam"). Two holes sat
under it, both in the one report path that returns a FILE:

  1. `POST /reports/school/{id}/export` called `_check_school` and nothing else.
     Every other report on that router resolves `_grade_filter` (#576); this one
     never did, and the task's query was

         WHERE se.school_id = $1 AND se.status = 'active'

     So a teacher assigned only to Grade 5 received a CSV of EVERY active
     student in the school — name, email, grade, units passed, average score.
     Those are educational records outside their assigned scope (FERPA), handed
     over in a downloadable file rather than glimpsed on a screen.

  2. `GET /reports/download/{export_id}` had no ownership check of any kind. It
     confirmed a file existed and served it to any authenticated teacher. The id
     is an unguessable UUID, so this was not trivially exploitable — but an id
     that leaked through a shared link, a log line or browser history handed
     another school its roster, and "hard to guess" is not an access control.

The second fix is STRUCTURAL: exports are written under
`exports/{school_id}/` and the handler reads from the caller's own directory.
There is no comparison to forget on a later edit — a path built from the
caller's token cannot name another school's file.

`allowed_grades=[]` (a teacher with no assignments) must export NOBODY. That is
why the query tests `$2 IS NULL` rather than truthiness: `[]` and `None` are
different answers, and collapsing them turns "sees nothing" into "sees
everything", which is the bug being fixed.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import make_teacher_token


async def _register_school(client: AsyncClient, suffix: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={
            "school_name": f"Export School{suffix}",
            "contact_email": f"export{suffix}{uuid.uuid4().hex[:8]}@school.example.com",
            "country": "IN",
            "password": "SecureTestPwd1!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _admin_headers(reg: dict) -> dict:
    token = make_teacher_token(
        teacher_id=reg["teacher_id"], school_id=reg["school_id"], role="school_admin"
    )
    return {"Authorization": f"Bearer {token}"}


async def _teacher_of_grades(client: AsyncClient, school_id: str, grades: list[int]) -> dict:
    teacher_id = str(uuid.uuid4())
    pool = client._transport.app.state.pool
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider, name, email,
                 role, account_status)
            VALUES ($1, $2, $3, 'local', 'Export Teacher', $4, 'teacher', 'active')
            """,
            uuid.UUID(teacher_id),
            uuid.UUID(school_id),
            f"local:{teacher_id}",
            f"export-teacher-{teacher_id[:8]}@example.com",
        )
        for g in grades:
            await conn.execute(
                "INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)"
                " VALUES ($1, $2, $3)",
                uuid.UUID(teacher_id),
                uuid.UUID(school_id),
                g,
            )
    token = make_teacher_token(teacher_id=teacher_id, school_id=school_id, role="teacher")
    return {"Authorization": f"Bearer {token}"}


# ── 1. The export carries the caller's grade scope ────────────────────────────


@pytest.mark.asyncio
async def test_a_teacher_export_is_scoped_to_their_grades(client, db_conn):
    """The hole. A Grade 5 teacher's export must not be a school-wide roster."""
    reg = await _register_school(client, "_scope")
    headers = await _teacher_of_grades(client, reg["school_id"], [5])

    sent: dict = {}
    with patch("src.core.celery_app.celery_app.send_task") as send:
        r = await client.post(
            f"/api/v1/reports/school/{reg['school_id']}/export",
            json={"report_type": "overview", "filters": {}},
            headers=headers,
        )
        assert r.status_code in (200, 201), r.text
        sent = send.call_args.kwargs["kwargs"]

    assert sent["allowed_grades"] == [5], (
        "the export task must receive the caller's entitlement, not None"
    )


@pytest.mark.asyncio
async def test_a_school_admin_export_is_unrestricted(client, db_conn):
    """`None` means the whole school, and a school_admin is a teacher superset
    under ADR-005. Scoping them down would break the legitimate case."""
    reg = await _register_school(client, "_admin")

    with patch("src.core.celery_app.celery_app.send_task") as send:
        r = await client.post(
            f"/api/v1/reports/school/{reg['school_id']}/export",
            json={"report_type": "overview", "filters": {}},
            headers=_admin_headers(reg),
        )
        assert r.status_code in (200, 201), r.text
        sent = send.call_args.kwargs["kwargs"]

    assert sent["allowed_grades"] is None


@pytest.mark.asyncio
async def test_a_teacher_with_no_grades_exports_nobody(client, db_conn):
    """`[]` and `None` are different answers and must never be collapsed. A
    teacher with no assignments has no cohort; if `[]` were treated as falsy and
    became `None`, their export would contain the entire school — a worse
    version of the bug being fixed."""
    reg = await _register_school(client, "_nograde")
    headers = await _teacher_of_grades(client, reg["school_id"], [])

    with patch("src.core.celery_app.celery_app.send_task") as send:
        r = await client.post(
            f"/api/v1/reports/school/{reg['school_id']}/export",
            json={"report_type": "overview", "filters": {}},
            headers=headers,
        )
        assert r.status_code in (200, 201), r.text
        sent = send.call_args.kwargs["kwargs"]

    assert sent["allowed_grades"] == [], "empty list, NOT None"
    assert sent["allowed_grades"] is not None


@pytest.mark.asyncio
async def test_export_for_another_school_is_still_refused(client, db_conn):
    """The pre-existing check must survive the change."""
    mine = await _register_school(client, "_mine")
    other = await _register_school(client, "_other")

    r = await client.post(
        f"/api/v1/reports/school/{other['school_id']}/export",
        json={"report_type": "overview", "filters": {}},
        headers=_admin_headers(mine),
    )
    assert r.status_code == 403, r.text


# ── 2. A download cannot cross a school boundary ──────────────────────────────


def _write_export(content_root: str, school_id: str, export_id: str) -> str:
    path = os.path.join(content_root, "exports", school_id)
    os.makedirs(path, exist_ok=True)
    full = os.path.join(path, f"{export_id}.csv")
    with open(full, "w") as f:
        f.write("name,grade\nA Student,5\n")
    return full


@pytest.mark.asyncio
async def test_a_teacher_cannot_download_another_schools_export(client, db_conn, tmp_path):
    """The hole. An export_id from School A, presented by School B's teacher,
    must not resolve — even though the file exists on disk."""
    owner = await _register_school(client, "_owner")
    stranger = await _register_school(client, "_stranger")
    export_id = str(uuid.uuid4())

    from config import settings

    with patch.object(settings, "CONTENT_STORE_PATH", str(tmp_path)):
        _write_export(str(tmp_path), owner["school_id"], export_id)

        mine = await client.get(
            f"/api/v1/reports/download/{export_id}", headers=_admin_headers(owner)
        )
        assert mine.status_code == 200, "the school that made it can read it"

        theirs = await client.get(
            f"/api/v1/reports/download/{export_id}", headers=_admin_headers(stranger)
        )
        assert theirs.status_code == 404, theirs.text


@pytest.mark.asyncio
async def test_a_non_uuid_export_id_cannot_walk_the_path(client, db_conn, tmp_path):
    """`export_id` lands in a filesystem path, so it is validated as a UUID. A
    traversal attempt must 404 rather than resolve anywhere."""
    reg = await _register_school(client, "_traverse")

    from config import settings

    with patch.object(settings, "CONTENT_STORE_PATH", str(tmp_path)):
        r = await client.get(
            "/api/v1/reports/download/..%2f..%2fetc%2fpasswd",
            headers=_admin_headers(reg),
        )
        assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_missing_export_still_404s(client, db_conn, tmp_path):
    """The ordinary not-ready case is unchanged, and reports the same 404 as a
    forbidden one — so the response cannot be used to probe whether another
    school's export exists."""
    reg = await _register_school(client, "_missing")

    from config import settings

    with patch.object(settings, "CONTENT_STORE_PATH", str(tmp_path)):
        r = await client.get(
            f"/api/v1/reports/download/{uuid.uuid4()}", headers=_admin_headers(reg)
        )
        assert r.status_code == 404
        # The app's exception handler FLATTENS the HTTPException detail dict, so
        # the error code is top-level rather than nested under "detail".
        assert r.json()["error"] == "export_not_found"
