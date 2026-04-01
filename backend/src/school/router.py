"""
backend/src/school/router.py

Phase 8–9 school endpoints.

Routes (all prefixed /api/v1 in main.py):

  POST /schools/register                        — create school + school_admin (public)
  GET  /schools/{school_id}                     — school profile (teacher-scoped)
  POST /schools/{school_id}/teachers/invite     — invite a teacher (school_admin only)
  POST /schools/{school_id}/enrolment           — upload student email roster (school_admin only)
  GET  /schools/{school_id}/enrolment           — get enrolment roster (school_admin only)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_teacher
from src.core.db import get_db
from src.school.enrolment_service import get_roster, upload_roster
from src.school.schemas import (
    EnrolmentRosterItem,
    EnrolmentRosterResponse,
    EnrolmentUploadRequest,
    EnrolmentUploadResponse,
    SchoolProfileResponse,
    SchoolRegisterRequest,
    SchoolRegisterResponse,
    TeacherGradeAssignRequest,
    TeacherGradeAssignResponse,
    TeacherInviteRequest,
    TeacherInviteResponse,
    TeacherRosterResponse,
)
from src.school.service import fetch_school, invite_teacher, register_school
from src.school.subscription_service import get_seat_usage
from src.utils.logger import get_logger

log = get_logger("school")
router = APIRouter(tags=["school"])


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ── School registration (public — no JWT required) ────────────────────────────


@router.post(
    "/schools/register",
    response_model=SchoolRegisterResponse,
    status_code=201,
)
async def register_school_endpoint(
    body: SchoolRegisterRequest,
    request: Request,
) -> SchoolRegisterResponse:
    """
    Register a new school.

    Auto-approves the school and creates a school_admin teacher account.
    Returns an access token for immediate use.
    """
    async with get_db(request) as conn:
        try:
            result = await register_school(conn, body.school_name, body.contact_email, body.country)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "A teacher account with that email already exists.",
                        "correlation_id": _cid(request),
                    },
                )
            raise
    return SchoolRegisterResponse(**result)


# ── School profile ────────────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}",
    response_model=SchoolProfileResponse,
)
async def get_school_profile(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> SchoolProfileResponse:
    """Return the profile for the teacher's school."""
    async with get_db(request) as conn:
        school = await fetch_school(conn, school_id, teacher["school_id"])
    if not school:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "detail": "School not found.",
                "correlation_id": _cid(request),
            },
        )
    return SchoolProfileResponse(**school)


# ── Teacher invite ────────────────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/teachers/invite",
    response_model=TeacherInviteResponse,
    status_code=201,
)
async def invite_teacher_endpoint(
    school_id: str,
    body: TeacherInviteRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherInviteResponse:
    """Invite a new teacher to the school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can invite teachers.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot invite to a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        # Seat limit check — only enforced if school has an active subscription
        sub_row = await conn.fetchrow(
            """
            SELECT max_teachers FROM school_subscriptions
            WHERE school_id = $1 AND status IN ('active', 'trialing')
            """,
            _uuid.UUID(school_id),
        )
        if sub_row is not None:
            usage = await get_seat_usage(conn, school_id)
            if usage["seats_used_teachers"] >= sub_row["max_teachers"]:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "seat_limit_reached",
                        "detail": "Teacher seat limit reached for this plan.",
                        "limit": sub_row["max_teachers"],
                        "correlation_id": _cid(request),
                    },
                )
        try:
            result = await invite_teacher(conn, school_id, body.name, body.email)
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "conflict",
                        "detail": "Teacher email already registered.",
                        "correlation_id": _cid(request),
                    },
                )
            raise
    return TeacherInviteResponse(**result)


# ── Enrolment roster upload ───────────────────────────────────────────────────


@router.post(
    "/schools/{school_id}/enrolment",
    response_model=EnrolmentUploadResponse,
    status_code=201,
)
async def upload_enrolment_roster(
    school_id: str,
    body: EnrolmentUploadRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> EnrolmentUploadResponse:
    """Upload a student email roster for the school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can upload rosters.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot manage enrolment for a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        # Seat limit check — only enforced if school has an active subscription
        sub_row = await conn.fetchrow(
            """
            SELECT max_students FROM school_subscriptions
            WHERE school_id = $1 AND status IN ('active', 'trialing')
            """,
            _uuid.UUID(school_id),
        )
        if sub_row is not None:
            usage = await get_seat_usage(conn, school_id)
            incoming = len([e for e in body.student_emails if str(e).strip()])
            if usage["seats_used_students"] + incoming > sub_row["max_students"]:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "seat_limit_reached",
                        "detail": "Enrolling these students would exceed the plan seat limit.",
                        "limit": sub_row["max_students"],
                        "used": usage["seats_used_students"],
                        "correlation_id": _cid(request),
                    },
                )
        result = await upload_roster(conn, school_id, [str(e) for e in body.student_emails])
    return EnrolmentUploadResponse(**result)


# ── Enrolment roster read ─────────────────────────────────────────────────────


@router.get(
    "/schools/{school_id}/enrolment",
    response_model=EnrolmentRosterResponse,
)
async def get_enrolment_roster(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> EnrolmentRosterResponse:
    """Fetch the student enrolment roster for a school (school_admin only)."""
    if teacher.get("role") != "school_admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Only school_admin can view rosters.",
                "correlation_id": _cid(request),
            },
        )
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view enrolment for a different school.",
                "correlation_id": _cid(request),
            },
        )
    async with get_db(request) as conn:
        rows = await get_roster(conn, school_id)
    return EnrolmentRosterResponse(roster=[EnrolmentRosterItem(**r) for r in rows])


# ── Teacher roster ────────────────────────────────────────────────────────────


@router.get("/schools/{school_id}/teachers", response_model=TeacherRosterResponse)
async def list_teachers(
    school_id: str,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherRosterResponse:
    """List all teachers in the school with their assigned grades."""
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot view teachers for a different school.",
                "correlation_id": _cid(request),
            },
        )
    import uuid as _uuid

    async with get_db(request) as conn:
        rows = await conn.fetch(
            """
            SELECT t.teacher_id::text, t.name, t.email, t.role,
                   t.account_status::text,
                   COALESCE(
                       array_agg(tga.grade ORDER BY tga.grade)
                       FILTER (WHERE tga.grade IS NOT NULL), '{}'
                   ) AS assigned_grades
            FROM teachers t
            LEFT JOIN teacher_grade_assignments tga
                ON tga.teacher_id = t.teacher_id
            WHERE t.school_id = $1
            GROUP BY t.teacher_id, t.name, t.email, t.role, t.account_status
            ORDER BY t.name
            """,
            _uuid.UUID(school_id),
        )
    return TeacherRosterResponse(
        teachers=[
            {
                "teacher_id": r["teacher_id"],
                "name": r["name"],
                "email": r["email"],
                "role": r["role"],
                "account_status": r["account_status"],
                "assigned_grades": list(r["assigned_grades"]),
            }
            for r in rows
        ]
    )


# ── Teacher grade assignment ───────────────────────────────────────────────────


@router.put(
    "/schools/{school_id}/teachers/{teacher_id}/grades",
    response_model=TeacherGradeAssignResponse,
)
async def assign_teacher_grades(
    school_id: str,
    teacher_id: str,
    body: TeacherGradeAssignRequest,
    request: Request,
    teacher: Annotated[dict, Depends(get_current_teacher)],
) -> TeacherGradeAssignResponse:
    """Replace the grade assignments for a teacher (any teacher in the school)."""
    if teacher["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Cannot manage teachers for a different school.",
                "correlation_id": _cid(request),
            },
        )
    # Validate grades
    invalid = [g for g in body.grades if g < 5 or g > 12]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_grades",
                "detail": f"Grades must be between 5 and 12. Invalid: {invalid}",
                "correlation_id": _cid(request),
            },
        )

    import uuid as _uuid

    tid = _uuid.UUID(teacher_id)
    sid = _uuid.UUID(school_id)

    async with get_db(request) as conn:
        # Verify the teacher belongs to this school
        exists = await conn.fetchval(
            "SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $2",
            tid, sid,
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": "Teacher not found in this school.",
                    "correlation_id": _cid(request),
                },
            )
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM teacher_grade_assignments WHERE teacher_id = $1", tid
            )
            if body.grades:
                await conn.executemany(
                    """
                    INSERT INTO teacher_grade_assignments (teacher_id, school_id, grade)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (teacher_id, grade) DO NOTHING
                    """,
                    [(tid, sid, g) for g in body.grades],
                )

    log.info(
        "teacher_grades_assigned",
        teacher_id=teacher_id,
        school_id=school_id,
        grades=sorted(body.grades),
    )
    return TeacherGradeAssignResponse(
        teacher_id=teacher_id,
        school_id=school_id,
        assigned_grades=sorted(body.grades),
    )
