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

from src.auth.service import create_internal_jwt, generate_default_password, hash_password
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
    password: str,
) -> dict:
    """
    Create a school and its first school_admin teacher in one transaction.

    The founder sets their own password directly — no default password / forced
    reset for the account creator (Phase A design, Section 4a).

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
        uuid.UUID(school_id),
        name,
        contact_email,
        country,
        enrolment_code,
    )

    # Seed the storage quota row — every school starts with 5 GB base allocation.
    await conn.execute(
        """
        INSERT INTO school_storage_quotas (school_id)
        VALUES ($1)
        ON CONFLICT DO NOTHING
        """,
        uuid.UUID(school_id),
    )

    teacher_id = str(uuid.uuid4())
    password_hash = await hash_password(password)

    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, auth_provider,
             name, email, password_hash, role, account_status, first_login)
        VALUES ($1, $2, $3, 'local', $4, $5, $6, 'school_admin', 'active', FALSE)
        """,
        uuid.UUID(teacher_id),
        uuid.UUID(school_id),
        f"local:{teacher_id}",
        name,
        contact_email,
        password_hash,
    )

    token = create_internal_jwt(
        {
            "teacher_id": teacher_id,
            "school_id": school_id,
            "role": "school_admin",
            "account_status": "active",
            "first_login": False,
        },
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
    Legacy invite flow (Auth0 path).  Creates a 'pending' teacher record
    that is activated when the teacher completes Auth0 sign-up.

    Kept for backward compatibility.  New provisioning uses provision_teacher().
    """
    teacher_id = str(uuid.uuid4())
    ext_auth_id = f"invite:{teacher_id}"

    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, name, email, role, account_status)
        VALUES ($1, $2, $3, $4, $5, 'teacher', 'pending')
        """,
        uuid.UUID(teacher_id),
        uuid.UUID(school_id),
        ext_auth_id,
        name,
        email,
    )

    log.info("teacher_invited", teacher_id=teacher_id, school_id=school_id)
    return {"teacher_id": teacher_id, "email": email, "role": "teacher"}


async def provision_teacher(
    conn: asyncpg.Connection,
    school_id: str,
    name: str,
    email: str,
    subject_specialisation: str | None = None,
) -> dict:
    """
    Create a school-provisioned teacher with local auth (Phase A).

    Generates a random default password, hashes it, and stores it.
    Returns the plain-text default password so the router can send it via email.
    Sets first_login=True so the client forces a password reset on first use.
    """
    teacher_id = str(uuid.uuid4())
    default_password = generate_default_password()
    password_hash = await hash_password(default_password)

    await conn.execute(
        """
        INSERT INTO teachers
            (teacher_id, school_id, external_auth_id, auth_provider,
             name, email, password_hash, role, account_status, first_login)
        VALUES ($1, $2, $3, 'local', $4, $5, $6, 'teacher', 'active', TRUE)
        """,
        uuid.UUID(teacher_id),
        uuid.UUID(school_id),
        f"local:{teacher_id}",
        name,
        email,
        password_hash,
    )

    log.info("teacher_provisioned", teacher_id=teacher_id, school_id=school_id)
    return {
        "teacher_id": teacher_id,
        "school_id": school_id,
        "name": name,
        "email": email,
        "role": "teacher",
        "default_password": default_password,
    }


async def provision_student(
    conn: asyncpg.Connection,
    school_id: str,
    name: str,
    email: str,
    grade: int,
) -> dict:
    """
    Create a school-provisioned student with local auth (Phase A).

    Generates a random default password, hashes it, and stores it.
    Returns the plain-text default password so the router can send it via email.
    Sets first_login=True so the client forces a password reset on first use.
    """
    student_id = str(uuid.uuid4())
    default_password = generate_default_password()
    password_hash = await hash_password(default_password)

    await conn.execute(
        """
        INSERT INTO students
            (student_id, school_id, external_auth_id, auth_provider,
             name, email, password_hash, grade, account_status, first_login)
        VALUES ($1, $2, $3, 'local', $4, $5, $6, $7, 'active', TRUE)
        """,
        uuid.UUID(student_id),
        uuid.UUID(school_id),
        f"local:{student_id}",
        name,
        email,
        password_hash,
        grade,
    )

    log.info("student_provisioned", student_id=student_id, school_id=school_id, grade=grade)
    return {
        "student_id": student_id,
        "school_id": school_id,
        "name": name,
        "email": email,
        "grade": grade,
        "default_password": default_password,
    }


async def reset_teacher_password(conn: asyncpg.Connection, school_id: str, teacher_id: str) -> dict:
    """
    Generate a new default password for a teacher and set first_login=True.

    Returns the new plain-text password so the router can email it.
    Only operates on teachers that belong to the given school.
    """
    new_password = generate_default_password()
    new_hash = await hash_password(new_password)

    row = await conn.fetchrow(
        """
        UPDATE teachers
           SET password_hash = $1,
               first_login   = TRUE,
               auth_provider = 'local'
         WHERE teacher_id = $2 AND school_id = $3
        RETURNING teacher_id::text, name, email
        """,
        new_hash,
        uuid.UUID(teacher_id),
        uuid.UUID(school_id),
    )
    if not row:
        return {}

    log.info("teacher_password_reset", teacher_id=teacher_id, school_id=school_id)
    return {"teacher_id": row["teacher_id"], "name": row["name"], "email": row["email"],
            "default_password": new_password}


async def reset_student_password(conn: asyncpg.Connection, school_id: str, student_id: str) -> dict:
    """
    Generate a new default password for a student and set first_login=True.

    Returns the new plain-text password so the router can email it.
    Only operates on students that belong to the given school.
    """
    new_password = generate_default_password()
    new_hash = await hash_password(new_password)

    row = await conn.fetchrow(
        """
        UPDATE students
           SET password_hash = $1,
               first_login   = TRUE,
               auth_provider = 'local'
         WHERE student_id = $2 AND school_id = $3
        RETURNING student_id::text, name, email
        """,
        new_hash,
        uuid.UUID(student_id),
        uuid.UUID(school_id),
    )
    if not row:
        return {}

    log.info("student_password_reset", student_id=student_id, school_id=school_id)
    return {"student_id": row["student_id"], "name": row["name"], "email": row["email"],
            "default_password": new_password}


async def promote_to_school_admin(conn: asyncpg.Connection, school_id: str, teacher_id: str) -> dict:
    """
    Promote an existing teacher in the school to the school_admin role.

    Multiple people can hold school_admin per school (Phase A, Q9 / Q18).
    Returns the updated teacher record, or empty dict if not found.
    """
    row = await conn.fetchrow(
        """
        UPDATE teachers SET role = 'school_admin'
         WHERE teacher_id = $1 AND school_id = $2
        RETURNING teacher_id::text, name, email, role
        """,
        uuid.UUID(teacher_id),
        uuid.UUID(school_id),
    )
    if not row:
        return {}

    log.info("teacher_promoted_to_admin", teacher_id=teacher_id, school_id=school_id)
    return dict(row)
