"""
backend/src/school/service.py

Business logic for school registration and teacher management.

School registration (Phase 8):
  - Auto-approve: no manual review step.
  - Creates school record + school_admin teacher in a single transaction.
  - Issues a teacher JWT immediately so the caller can start using the API.

Teacher invite:
  - school_admin can invite additional teachers to their school.
  - Invited teacher gets account_status='pending' until they complete Auth0 sign-up.
"""

from __future__ import annotations

import re
import uuid

import asyncpg
from config import settings

from src.auth.service import create_internal_jwt
from src.utils.logger import get_logger

log = get_logger("school")


def _gen_enrolment_code(school_name: str) -> str:
    """Derive a short enrolment code from the school name + random suffix."""
    abbr = re.sub(r"[^A-Za-z0-9]", "", school_name).upper()[:6] or "SCHL"
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{abbr}-{suffix}"


async def register_school(
    conn: asyncpg.Connection,
    name: str,
    contact_email: str,
    country: str,
) -> dict:
    """
    Create a school and its first school_admin teacher in one transaction.

    Returns school_id, teacher_id, and a short-lived access token so the
    caller can immediately call teacher-scoped endpoints.
    """
    school_id = str(uuid.uuid4())
    enrolment_code = _gen_enrolment_code(name)

    await conn.execute(
        """
        INSERT INTO schools (school_id, name, contact_email, country, enrolment_code, status)
        VALUES ($1, $2, $3, $4, $5, 'active')
        """,
        uuid.UUID(school_id), name, contact_email, country, enrolment_code,
    )

    teacher_id = str(uuid.uuid4())
    # external_auth_id is a placeholder until the teacher links their Auth0 account.
    ext_auth_id = f"school_reg:{teacher_id}"

    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, name, email, role, account_status)
        VALUES ($1, $2, $3, $4, $5, 'school_admin', 'active')
        """,
        uuid.UUID(teacher_id), uuid.UUID(school_id),
        ext_auth_id, name, contact_email,
    )

    token = create_internal_jwt(
        {"teacher_id": teacher_id, "school_id": school_id, "role": "school_admin"},
        settings.JWT_SECRET,
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    log.info("school_registered", school_id=school_id, teacher_id=teacher_id)
    return {
        "school_id": school_id,
        "teacher_id": teacher_id,
        "access_token": token,
        "role": "school_admin",
    }


async def fetch_school(
    conn: asyncpg.Connection,
    school_id: str,
    requesting_school_id: str,
) -> dict | None:
    """
    Return school profile.  Teachers may only view their own school.
    """
    if school_id != requesting_school_id:
        return None
    row = await conn.fetchrow(
        """
        SELECT school_id::text, name, contact_email, country, enrolment_code,
               status::text, created_at
        FROM schools
        WHERE school_id = $1
        """,
        uuid.UUID(school_id),
    )
    return dict(row) if row else None


async def invite_teacher(
    conn: asyncpg.Connection,
    school_id: str,
    name: str,
    email: str,
) -> dict:
    """
    Create a teacher record for an invited user.

    The teacher starts as 'pending'; they complete onboarding via Auth0 sign-up
    which will call POST /auth/teacher/exchange and activate the account.
    """
    teacher_id = str(uuid.uuid4())
    ext_auth_id = f"invite:{teacher_id}"

    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, name, email, role, account_status)
        VALUES ($1, $2, $3, $4, $5, 'teacher', 'pending')
        """,
        uuid.UUID(teacher_id), uuid.UUID(school_id),
        ext_auth_id, name, email,
    )

    log.info("teacher_invited", teacher_id=teacher_id, school_id=school_id)
    return {"teacher_id": teacher_id, "email": email, "role": "teacher"}
