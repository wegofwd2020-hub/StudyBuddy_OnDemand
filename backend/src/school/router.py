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
    TeacherInviteRequest,
    TeacherInviteResponse,
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
