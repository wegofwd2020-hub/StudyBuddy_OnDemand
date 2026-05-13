"""
backend/src/admin/demo_test_runs.py

Admin endpoints for the visitor "test run" flow (POST /demo/test-run/request).

Routes (all prefixed /api/v1 in app_factory.py, require admin JWT):
  GET    /admin/demo/test-runs              — list all test-run requests
  DELETE /admin/demo/test-runs/by-email     — purge both student + teacher
                                               demo state for one email so the
                                               visitor can request a fresh
                                               test run

Identification: a test-run always writes a `+student@` row to demo_requests AND
a paired `+teacher@` row to demo_teacher_requests sharing the same verification
token. We list / reset by the student-side request — the teacher side is
derived by swapping the plus-tag.

Access: super_admin and product_admin.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.auth.dependencies import get_current_admin
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("admin.demo.test_runs")
router = APIRouter(tags=["admin-demo-test-runs"])


# ── RBAC dependency ───────────────────────────────────────────────────────────


def _require_demo_manage():
    async def dep(
        request: Request,
        admin: Annotated[dict, Depends(get_current_admin)],
    ) -> dict:
        role = admin.get("role", "")
        if role not in ("super_admin", "product_admin"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "detail": "super_admin or product_admin role required.",
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                },
            )
        return admin

    return dep


_demo_manage = _require_demo_manage()


# ── Schemas ───────────────────────────────────────────────────────────────────


class TestRunItem(BaseModel):
    """One visitor's test-run state, joining student + teacher sides."""

    # Visitor-visible identity
    name: str | None
    email: str  # un-tagged original — e.g. "siva@example.com"
    requested_at: datetime
    status: str  # "pending" | "verified" | "expired" | "revoked" (from request)

    # Per-role login emails (what the credentials email tells them to use)
    student_email: str
    teacher_email: str

    # Provisioned account expiry — null until the visitor clicks the
    # verification link. Once verified, both are populated.
    student_expires_at: datetime | None
    teacher_expires_at: datetime | None
    verification_expires_at: datetime | None
    revoked_at: datetime | None


class TestRunListResponse(BaseModel):
    items: list[TestRunItem]
    total: int
    page: int
    page_size: int


class TestRunDeleteResponse(BaseModel):
    """Number of rows touched per table — useful for telemetry / debugging."""

    student_requests_deleted: int
    teacher_requests_deleted: int
    students_deleted: int
    teachers_deleted: int
    classrooms_deleted: int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _untag_email(plus_tagged: str) -> str:
    """`siva+student@example.com` → `siva@example.com`."""
    local, _, domain = plus_tagged.partition("@")
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def _retag_email(plus_tagged: str, new_tag: str) -> str:
    """`siva+student@example.com` → `siva+teacher@example.com`."""
    local, _, domain = plus_tagged.partition("@")
    local = local.split("+", 1)[0]
    return f"{local}+{new_tag}@{domain}"


# ── GET /admin/demo/test-runs ─────────────────────────────────────────────────


@router.get("/admin/demo/test-runs", response_model=TestRunListResponse)
async def list_test_runs(
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
    email: str | None = Query(default=None, description="Partial original-email match"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """List all visitor test-runs, newest first.

    Test-runs are identified by the `+student@` tag on demo_requests.email — that's
    the canonical row written by POST /demo/test-run/request. The teacher side
    is joined by swapping the tag.
    """
    offset = (page - 1) * page_size

    # Allow filtering by the un-tagged email the visitor actually typed. We match
    # against the +student-tagged form internally.
    email_filter_sql = ""
    params: list = []
    p = 1
    if email:
        email_filter_sql = f"AND dr.email ILIKE ${p}"
        params.append(f"%{email}%")
        p += 1

    async with get_db(request) as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                dr.id            AS request_id,
                dr.name,
                dr.email         AS student_request_email,
                dr.requested_at,
                dr.status        AS request_status,
                da.expires_at    AS student_expires_at,
                da.revoked_at    AS student_revoked_at,
                dta.expires_at   AS teacher_expires_at,
                dta.revoked_at   AS teacher_revoked_at,
                (
                    SELECT dv.expires_at
                    FROM demo_verifications dv
                    WHERE dv.request_id = dr.id
                      AND dv.used_at IS NULL
                      AND dv.expires_at > NOW()
                    ORDER BY dv.created_at DESC
                    LIMIT 1
                ) AS verification_expires_at
            FROM demo_requests dr
            LEFT JOIN demo_accounts da ON da.request_id = dr.id
            LEFT JOIN demo_teacher_requests dtr
                   ON dtr.email = REPLACE(dr.email, '+student@', '+teacher@')
            LEFT JOIN demo_teacher_accounts dta ON dta.request_id = dtr.id
            WHERE dr.email LIKE '%+student@%'
              {email_filter_sql}
            ORDER BY dr.requested_at DESC
            LIMIT ${p} OFFSET ${p + 1}
            """,
            *params,
            page_size,
            offset,
        )

        total = await conn.fetchval(
            f"""
            SELECT COUNT(*) FROM demo_requests dr
            WHERE dr.email LIKE '%+student@%' {email_filter_sql}
            """,
            *params,
        )

    items = []
    for r in rows:
        student_email = r["student_request_email"]
        items.append(
            TestRunItem(
                name=r["name"],
                email=_untag_email(student_email),
                requested_at=r["requested_at"],
                status=r["request_status"],
                student_email=student_email,
                teacher_email=_retag_email(student_email, "teacher"),
                student_expires_at=r["student_expires_at"],
                teacher_expires_at=r["teacher_expires_at"],
                verification_expires_at=r["verification_expires_at"],
                revoked_at=r["student_revoked_at"] or r["teacher_revoked_at"],
            )
        )

    return TestRunListResponse(
        items=items,
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


# ── DELETE /admin/demo/test-runs/by-email ─────────────────────────────────────


@router.delete(
    "/admin/demo/test-runs/by-email",
    response_model=TestRunDeleteResponse,
)
async def delete_test_run_by_email(
    request: Request,
    admin: Annotated[dict, Depends(_demo_manage)],
    email: str = Query(..., description="Original (un-tagged) email the visitor submitted"),
):
    """Purge all test-run state for one visitor email so they can re-request.

    Removes both student and teacher sides:
      - demo_requests + demo_teacher_requests (cascades clean up verifications
        and demo_accounts / demo_teacher_accounts via ON DELETE CASCADE).
      - students + teachers rows with auth_provider='demo' so the unique
        constraint on email is freed.

    Idempotent: deleting an email that has no test-run state returns zeroes
    rather than raising.
    """
    cid = getattr(request.state, "correlation_id", "")
    admin_id = admin.get("admin_id")

    # Reject obviously bad input — the caller can pass any string.
    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "detail": "email parameter must be a valid email address.",
                "correlation_id": cid,
            },
        )

    student_email = _retag_email(email, "student")
    teacher_email = _retag_email(email, "teacher")

    async with get_db(request) as conn:
        async with conn.transaction():
            # Capture the student_id / teacher_id BEFORE the cascade drops the
            # demo_accounts rows so we can clean up the auth_provider='demo'
            # rows from students / teachers afterwards.
            student_ids = [
                r["student_id"]
                for r in await conn.fetch(
                    """
                    SELECT da.student_id
                    FROM demo_accounts da
                    JOIN demo_requests dr ON dr.id = da.request_id
                    WHERE dr.email = $1
                    """,
                    student_email,
                )
            ]
            teacher_ids = [
                r["teacher_id"]
                for r in await conn.fetch(
                    """
                    SELECT dta.teacher_id
                    FROM demo_teacher_accounts dta
                    JOIN demo_teacher_requests dtr ON dtr.id = dta.request_id
                    WHERE dtr.email = $1
                    """,
                    teacher_email,
                )
            ]

            student_req_deleted = await conn.fetchval(
                """
                WITH d AS (DELETE FROM demo_requests WHERE email = $1 RETURNING 1)
                SELECT COUNT(*) FROM d
                """,
                student_email,
            )
            teacher_req_deleted = await conn.fetchval(
                """
                WITH d AS (DELETE FROM demo_teacher_requests WHERE email = $1 RETURNING 1)
                SELECT COUNT(*) FROM d
                """,
                teacher_email,
            )

            students_deleted = 0
            for sid in student_ids:
                students_deleted += await conn.fetchval(
                    """
                    WITH d AS (
                        DELETE FROM students
                        WHERE student_id = $1 AND auth_provider = 'demo'
                        RETURNING 1
                    )
                    SELECT COUNT(*) FROM d
                    """,
                    sid,
                )

            # Drop classrooms owned by the demo teacher BEFORE deleting the
            # teacher row. classrooms.teacher_id is ON DELETE SET NULL, so
            # without this step the per-visitor classroom would linger as
            # an orphaned/leaderless row in the school. classroom_students
            # + classroom_packages cascade off classroom_id.
            classrooms_deleted = 0
            for tid in teacher_ids:
                classrooms_deleted += await conn.fetchval(
                    """
                    WITH d AS (
                        DELETE FROM classrooms
                        WHERE teacher_id = $1
                        RETURNING 1
                    )
                    SELECT COUNT(*) FROM d
                    """,
                    tid,
                )

            teachers_deleted = 0
            for tid in teacher_ids:
                teachers_deleted += await conn.fetchval(
                    """
                    WITH d AS (
                        DELETE FROM teachers
                        WHERE teacher_id = $1 AND auth_provider = 'demo'
                        RETURNING 1
                    )
                    SELECT COUNT(*) FROM d
                    """,
                    tid,
                )

    log.info(
        "test_run_purged",
        email=email,
        admin_id=admin_id,
        student_requests=student_req_deleted,
        teacher_requests=teacher_req_deleted,
        students=students_deleted,
        teachers=teachers_deleted,
        classrooms=classrooms_deleted,
    )

    return TestRunDeleteResponse(
        student_requests_deleted=int(student_req_deleted or 0),
        teacher_requests_deleted=int(teacher_req_deleted or 0),
        students_deleted=int(students_deleted or 0),
        teachers_deleted=int(teachers_deleted or 0),
        classrooms_deleted=int(classrooms_deleted or 0),
    )
