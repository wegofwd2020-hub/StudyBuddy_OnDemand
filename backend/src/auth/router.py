"""
backend/src/auth/router.py

Student and teacher auth routes (Auth0 external track).

Routes:
  POST /auth/exchange              — Auth0 id_token → internal JWT (student)
  POST /auth/teacher/exchange      — Auth0 id_token → internal JWT (teacher)
  POST /auth/refresh               — refresh token → new JWT
  POST /auth/logout                — invalidate refresh token
  POST /auth/forgot-password       — trigger Auth0 password reset (always 200)
  PATCH /student/profile           — update student name/locale/grade
  GET   /auth/settings             — get display_name, locale, notification preferences
  PATCH /auth/settings             — update display_name, locale, notification preferences
  DELETE /auth/account             — soft-delete + GDPR Celery task

All prefixed with /api/v1 in main.py.
"""

from __future__ import annotations

from typing import Annotated

from config import settings
from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import get_current_student
from src.auth.schemas import (
    ForgotPasswordRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    StudentProfileUpdate,
    StudentPublic,
    TeacherPublic,
    TeacherTokenExchangeResponse,
    TokenExchangeRequest,
    TokenExchangeResponse,
)
from src.auth.service import (
    _hash_refresh_token,
    create_internal_jwt,
    generate_refresh_token,
    trigger_auth0_password_reset,
    upsert_student,
    upsert_teacher,
    verify_auth0_teacher_token,
    verify_auth0_token,
)
from src.core.db import get_db
from src.core.events import emit_event, write_audit_log
from src.core.observability import auth_exchanges_total, auth_failures_total
from src.core.redis_client import get_redis
from src.school.enrolment_service import link_student
from src.utils.logger import get_logger

log = get_logger("auth")
router = APIRouter(tags=["auth"])

_REFRESH_TTL = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400  # seconds


# ── Student exchange ──────────────────────────────────────────────────────────


@router.post("/auth/exchange", response_model=TokenExchangeResponse)
async def exchange_token(body: TokenExchangeRequest, request: Request):
    """
    Exchange an Auth0 id_token for an internal JWT + refresh token.

    Creates the student record on first login (upsert).
    Returns 403 if the account is suspended or pending.
    """
    cid = getattr(request.state, "correlation_id", "")

    claims = await verify_auth0_token(body.id_token)

    auth0_sub: str = claims.get("sub", "")
    email: str = claims.get("email", "")
    name: str = claims.get("name", email.split("@")[0])
    locale: str = claims.get("locale", "en")
    if locale not in ("en", "fr", "es"):
        locale = "en"

    # Grade must come from app_metadata (set during registration).
    grade_raw = claims.get("https://studybuddy.app/grade", claims.get("grade", 8))
    try:
        grade = int(grade_raw)
    except (TypeError, ValueError):
        grade = 8
    if not (5 <= grade <= 12):
        grade = 8

    # COPPA: Auth0 post-registration Action sets this claim for students under 13.
    requires_parental_consent: bool = bool(
        claims.get("https://studybuddy.app/requires_parental_consent", False)
    )

    async with get_db(request) as conn:
        student = await upsert_student(
            request.app.state.pool,
            auth0_sub,
            name,
            email,
            grade,
            locale,
            requires_parental_consent=requires_parental_consent,
        )
        # Phase 9: link to pending enrolment if one exists for this email.
        await link_student(conn, str(student["student_id"]), email)
        # Re-fetch student to capture any school_id set by link_student.
        refreshed = await conn.fetchrow(
            "SELECT school_id FROM students WHERE student_id = $1",
            student["student_id"],
        )
        if refreshed and refreshed["school_id"] is not None:
            student = {**student, "school_id": refreshed["school_id"]}

    account_status: str = student["account_status"]

    if account_status == "pending":
        auth_failures_total.labels(reason="account_pending").inc()
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_pending",
                "detail": "Account awaiting parental consent.",
                "correlation_id": cid,
            },
        )
    if account_status == "suspended":
        auth_failures_total.labels(reason="account_suspended").inc()
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_suspended",
                "detail": "Account has been suspended.",
                "correlation_id": cid,
            },
        )
    if account_status == "deleted":
        auth_failures_total.labels(reason="account_deleted").inc()
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Account has been deleted.",
                "correlation_id": cid,
            },
        )

    student_id = str(student["student_id"])
    jwt_payload = {
        "student_id": student_id,
        "grade": student["grade"],
        "locale": student["locale"],
        "role": "student",
        "account_status": account_status,
    }
    token = create_internal_jwt(
        jwt_payload, settings.JWT_SECRET, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    refresh = generate_refresh_token()
    redis = get_redis(request)
    await redis.set(
        f"refresh:{_hash_refresh_token(refresh)}",
        student_id,
        ex=_REFRESH_TTL,
    )

    auth_exchanges_total.labels(track="student").inc()
    emit_event("auth", "token_issued", student_id=student_id, track="student")
    write_audit_log("student_login", "student", student["student_id"])

    return TokenExchangeResponse(
        token=token,
        refresh_token=refresh,
        student_id=student["student_id"],
        student=StudentPublic(
            student_id=student["student_id"],
            name=student["name"],
            grade=student["grade"],
            locale=student["locale"],
            account_status=account_status,
        ),
    )


# ── Teacher exchange ──────────────────────────────────────────────────────────


@router.post("/auth/teacher/exchange", response_model=TeacherTokenExchangeResponse)
async def exchange_teacher_token(body: TokenExchangeRequest, request: Request):
    """Exchange Auth0 id_token for teacher internal JWT."""
    cid = getattr(request.state, "correlation_id", "")

    claims = await verify_auth0_teacher_token(body.id_token)

    auth0_sub: str = claims.get("sub", "")
    email: str = claims.get("email", "")
    name: str = claims.get("name", email.split("@")[0])
    role: str = claims.get("https://studybuddy.app/role", "teacher")
    if role not in ("teacher", "school_admin"):
        role = "teacher"

    teacher = await upsert_teacher(request.app.state.pool, auth0_sub, None, name, email, role)

    account_status: str = teacher["account_status"]
    if account_status == "suspended":
        auth_failures_total.labels(reason="account_suspended").inc()
        raise HTTPException(
            status_code=403,
            detail={
                "error": "account_suspended",
                "detail": "Account has been suspended.",
                "correlation_id": cid,
            },
        )

    teacher_id = str(teacher["teacher_id"])
    school_id = teacher.get("school_id")

    jwt_payload = {
        "teacher_id": teacher_id,
        "school_id": str(school_id) if school_id else None,
        "role": role,
        "account_status": account_status,
    }
    token = create_internal_jwt(
        jwt_payload, settings.JWT_SECRET, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    refresh = generate_refresh_token()
    redis = get_redis(request)
    await redis.set(
        f"refresh:{_hash_refresh_token(refresh)}",
        teacher_id,
        ex=_REFRESH_TTL,
    )

    auth_exchanges_total.labels(track="teacher").inc()
    emit_event("auth", "token_issued", teacher_id=teacher_id, track="teacher")

    return TeacherTokenExchangeResponse(
        token=token,
        refresh_token=refresh,
        teacher_id=teacher["teacher_id"],
        teacher=TeacherPublic(
            teacher_id=teacher["teacher_id"],
            school_id=teacher["school_id"],
            name=teacher["name"],
            email=teacher["email"],
            role=teacher["role"],
            account_status=account_status,
        ),
    )


# ── Refresh ───────────────────────────────────────────────────────────────────


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest, request: Request):
    """Exchange a valid refresh token for a new access JWT."""
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    key = f"refresh:{_hash_refresh_token(body.refresh_token)}"
    user_id_bytes = await redis.get(key)
    if not user_id_bytes:
        auth_failures_total.labels(reason="refresh_token_invalid").inc()
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthenticated",
                "detail": "Invalid or expired refresh token.",
                "correlation_id": cid,
            },
        )

    user_id: str = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes

    # Determine user type by querying DB.
    async with get_db(request) as conn:
        student = await conn.fetchrow(
            "SELECT student_id, grade, locale, account_status FROM students WHERE student_id = $1",
            user_id,
        )
        if student:
            payload = {
                "student_id": str(student["student_id"]),
                "grade": student["grade"],
                "locale": student["locale"],
                "role": "student",
                "account_status": student["account_status"],
            }
            secret = settings.JWT_SECRET
        else:
            teacher = await conn.fetchrow(
                "SELECT teacher_id, school_id, role, account_status FROM teachers WHERE teacher_id = $1",
                user_id,
            )
            if not teacher:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "unauthenticated",
                        "detail": "User not found.",
                        "correlation_id": cid,
                    },
                )
            payload = {
                "teacher_id": str(teacher["teacher_id"]),
                "school_id": str(teacher["school_id"]) if teacher["school_id"] else None,
                "role": teacher["role"],
                "account_status": teacher["account_status"],
            }
            secret = settings.JWT_SECRET

    token = create_internal_jwt(payload, secret, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return RefreshResponse(token=token)


# ── Logout ────────────────────────────────────────────────────────────────────


@router.post("/auth/logout")
async def logout(body: LogoutRequest, request: Request):
    """Delete the refresh token from Redis."""
    redis = get_redis(request)
    await redis.delete(f"refresh:{_hash_refresh_token(body.refresh_token)}")
    emit_event("auth", "logout")
    return {}


# ── Forgot password (always 200) ──────────────────────────────────────────────


@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """
    Trigger Auth0 password reset email.

    Always returns HTTP 200 regardless of whether the email is registered.
    Different responses would leak registered email addresses.
    """
    # Fire and forget — do not await or surface errors.
    try:
        await trigger_auth0_password_reset(str(body.email))
    except Exception:
        pass
    emit_event("auth", "forgot_password_requested")
    return {}


# ── Student profile update ────────────────────────────────────────────────────


@router.patch("/student/profile")
async def update_student_profile(
    body: StudentProfileUpdate,
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """Update student name, locale, or grade."""
    student_id = student["student_id"]

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.locale is not None:
        updates["locale"] = body.locale

    if not updates and body.grade is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "detail": "No fields to update."},
        )

    async with get_db(request) as conn:
        # Grade is managed exclusively by the school once a student is enrolled.
        # Reject self-grade-change; school admin uses the assignment endpoint.
        if body.grade is not None:
            school_id_row = await conn.fetchval(
                "SELECT school_id FROM students WHERE student_id = $1",
                student_id,
            )
            if school_id_row is not None:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "forbidden",
                        "detail": "Grade is managed by your school and cannot be changed here.",
                    },
                )
            updates["grade"] = body.grade

        if not updates:
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "detail": "No fields to update."},
            )

        set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(updates))
        values = [student_id, *updates.values()]
        row = await conn.fetchrow(
            f"UPDATE students SET {set_clause} WHERE student_id = $1 RETURNING *",
            *values,
        )

    if row is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "Student not found."})

    emit_event("auth", "profile_updated", student_id=student_id)
    return {
        "student_id": str(row["student_id"]),
        "name": row["name"],
        "grade": row["grade"],
        "locale": row["locale"],
        "account_status": row["account_status"],
    }


# ── Student settings (display_name, locale, notifications) ───────────────────


@router.get("/auth/settings")
async def get_settings(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """Return display name, locale, and notification preferences for the student."""
    student_id = student["student_id"]

    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT name, locale FROM students WHERE student_id = $1",
            student_id,
        )
        notif = await conn.fetchrow(
            """
            SELECT streak_reminders, weekly_summary, quiz_nudges
            FROM notification_preferences
            WHERE student_id = $1
            """,
            student_id,
        )

    # notification_preferences row may not exist yet for older accounts
    notifications = {
        "streak_reminders": notif["streak_reminders"] if notif else True,
        "weekly_summary": notif["weekly_summary"] if notif else True,
        "quiz_nudges": notif["quiz_nudges"] if notif else True,
    }

    return {
        "display_name": row["name"],
        "locale": row["locale"],
        "notifications": notifications,
    }


@router.patch("/auth/settings")
async def update_settings(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
    body: dict,
):
    """Update display name, locale, and/or notification preferences."""
    student_id = student["student_id"]

    async with get_db(request) as conn:
        # Update students table fields if provided
        student_updates = {}
        if "display_name" in body and body["display_name"] is not None:
            student_updates["name"] = body["display_name"]
        if "locale" in body and body["locale"] in ("en", "fr", "es"):
            student_updates["locale"] = body["locale"]

        if student_updates:
            set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(student_updates))
            await conn.execute(
                f"UPDATE students SET {set_clause} WHERE student_id = $1",
                student_id,
                *student_updates.values(),
            )

        # Upsert notification preferences if provided
        notif = body.get("notifications")
        if isinstance(notif, dict):
            await conn.execute(
                """
                INSERT INTO notification_preferences
                    (student_id, streak_reminders, weekly_summary, quiz_nudges, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (student_id) DO UPDATE SET
                    streak_reminders = EXCLUDED.streak_reminders,
                    weekly_summary   = EXCLUDED.weekly_summary,
                    quiz_nudges      = EXCLUDED.quiz_nudges,
                    updated_at       = NOW()
                """,
                student_id,
                bool(notif.get("streak_reminders", True)),
                bool(notif.get("weekly_summary", True)),
                bool(notif.get("quiz_nudges", True)),
            )

    emit_event("auth", "settings_updated", student_id=str(student_id))
    return {}


# ── Account deletion (GDPR) ───────────────────────────────────────────────────


@router.delete("/auth/account")
async def delete_account(
    request: Request,
    student: Annotated[dict, Depends(get_current_student)],
):
    """
    Initiate GDPR account deletion.

    Soft-deletes the account immediately and dispatches a Celery task
    to anonymise PII and delete from Auth0.  Always returns 200.
    """
    from src.auth.tasks import gdpr_delete_account

    student_id = student["student_id"]

    # Fetch auth0 sub for Celery task.
    async with get_db(request) as conn:
        row = await conn.fetchrow(
            "SELECT external_auth_id FROM students WHERE student_id = $1",
            student_id,
        )

    if row:
        gdpr_delete_account.delay(student_id, row["external_auth_id"])

    emit_event("auth", "account_deletion_requested", student_id=student_id)
    write_audit_log("account_deletion_requested", "student", student_id)
    return {}
