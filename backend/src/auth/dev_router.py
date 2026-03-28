"""
backend/src/auth/dev_router.py

Development-only auth endpoints. Only registered when APP_ENV=development.

Route:
  POST /auth/dev-login   — issue a long-lived JWT for the seeded dev
                           student or teacher; creates records on first call.

WARNING: This router MUST NEVER be registered in production. The guard in
main.py checks settings.APP_ENV == "development" before including it.
"""

from __future__ import annotations

import uuid
from typing import Literal

from config import settings
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.auth.service import create_internal_jwt
from src.core.db import get_db
from src.utils.logger import get_logger

log = get_logger("auth.dev")
router = APIRouter(tags=["dev"])

_DEV_STUDENT_SUB      = "dev|student-001"
_DEV_TEACHER_SUB      = "dev|teacher-001"
_DEV_SCHOOL_ADMIN_SUB = "dev|school-admin-001"
_DEV_SCHOOL_ID        = uuid.UUID("00000000-0000-0000-0000-000000000001")

# 7-day tokens — long enough for a testing session
_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


class DevLoginRequest(BaseModel):
    role: Literal["student", "teacher", "school_admin"]


class DevLoginResponse(BaseModel):
    token: str
    name: str
    email: str
    role: str


@router.post("/auth/dev-login", response_model=DevLoginResponse)
async def dev_login(body: DevLoginRequest, request: Request) -> DevLoginResponse:
    """
    Issue a long-lived JWT for the seeded dev student or teacher.
    Creates the DB records on first call (idempotent).
    Only available when APP_ENV=development.
    """
    if settings.APP_ENV != "development":
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "detail": "Dev login is only available in development mode."},
        )

    async with get_db(request) as conn:
        if body.role == "student":
            row = await conn.fetchrow(
                "SELECT student_id, name, email, grade, locale, account_status FROM students WHERE external_auth_id = $1",
                _DEV_STUDENT_SUB,
            )
            if row is None:
                row = await conn.fetchrow(
                    """
                    INSERT INTO students
                        (external_auth_id, auth_provider, name, email, grade, locale, account_status)
                    VALUES ($1, 'dev', 'Dev Student', 'dev.student@studybuddy.dev', 8, 'en', 'active')
                    RETURNING student_id, name, email, grade, locale, account_status
                    """,
                    _DEV_STUDENT_SUB,
                )
            if row is None:
                raise HTTPException(status_code=500, detail={"error": "internal_error", "detail": "Failed to create dev student."})

            # Give dev student a premium entitlement (bypasses the 2-lesson free-tier paywall)
            await conn.execute(
                """
                INSERT INTO student_entitlements (student_id, plan, lessons_accessed, valid_until)
                VALUES ($1, 'premium', 0, NOW() + INTERVAL '1 year')
                ON CONFLICT (student_id) DO UPDATE
                    SET plan = 'premium', valid_until = NOW() + INTERVAL '1 year'
                """,
                row["student_id"],
            )

            token = create_internal_jwt(
                {
                    "student_id": str(row["student_id"]),
                    "role": "student",
                    "grade": row["grade"],
                    "locale": row["locale"],
                    "account_status": row["account_status"],
                },
                settings.JWT_SECRET,
                _TOKEN_EXPIRE_MINUTES,
            )
            log.info("dev_student_login", student_id=str(row["student_id"]))
            return DevLoginResponse(token=token, name=row["name"], email=row["email"], role="student")

        # ── Teacher / School Admin ────────────────────────────────────────────
        # Ensure dev school exists first (teachers require a school_id FK).
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, contact_email, country, enrolment_code, status)
            VALUES ($1, 'Dev School', 'dev@studybuddy.dev', 'CA', 'DEVSCHOOL01', 'active')
            ON CONFLICT (school_id) DO NOTHING
            """,
            _DEV_SCHOOL_ID,
        )

        if body.role == "school_admin":
            ext_sub = _DEV_SCHOOL_ADMIN_SUB
            dev_name = "Dev School Admin"
            dev_email = "dev.schooladmin@studybuddy.dev"
            db_role = "school_admin"
        else:
            ext_sub = _DEV_TEACHER_SUB
            dev_name = "Dev Teacher"
            dev_email = "dev.teacher@studybuddy.dev"
            db_role = "teacher"

        teacher_row = await conn.fetchrow(
            "SELECT teacher_id, name, email, school_id, role, account_status FROM teachers WHERE external_auth_id = $1",
            ext_sub,
        )
        if teacher_row is None:
            teacher_row = await conn.fetchrow(
                """
                INSERT INTO teachers (school_id, external_auth_id, auth_provider, name, email, role, account_status)
                VALUES ($1, $2, 'dev', $3, $4, $5, 'active')
                RETURNING teacher_id, name, email, school_id, role, account_status
                """,
                _DEV_SCHOOL_ID,
                ext_sub,
                dev_name,
                dev_email,
                db_role,
            )
        if teacher_row is None:
            raise HTTPException(status_code=500, detail={"error": "internal_error", "detail": f"Failed to create dev {body.role}."})

        token = create_internal_jwt(
            {
                "teacher_id": str(teacher_row["teacher_id"]),
                "school_id": str(teacher_row["school_id"]),
                "role": teacher_row["role"],
                "account_status": teacher_row["account_status"],
            },
            settings.JWT_SECRET,
            _TOKEN_EXPIRE_MINUTES,
        )
        log.info("dev_teacher_login", teacher_id=str(teacher_row["teacher_id"]), role=teacher_row["role"])
        return DevLoginResponse(token=token, name=teacher_row["name"], email=teacher_row["email"], role=teacher_row["role"])
