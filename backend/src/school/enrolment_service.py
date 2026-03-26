"""
backend/src/school/enrolment_service.py

Phase 9 enrolment business logic.

Functions:
  upload_roster     — teacher uploads a list of student emails; creates pending enrolment rows
  get_roster        — fetch all enrolment rows for a school
  link_student      — called on student login; links student_id to any pending enrolment by email
"""

from __future__ import annotations

import uuid
from typing import List, Optional

import asyncpg

from src.utils.logger import get_logger

log = get_logger("enrolment")


async def upload_roster(
    conn: asyncpg.Connection,
    school_id: str,
    student_emails: List[str],
) -> dict:
    """
    Upsert enrolment rows for the given email list.

    - Already-active enrolments are counted but not modified.
    - New emails get status='pending'.
    - Emails already in the roster (any status) are counted as already_enrolled.
    - Returns {enrolled, already_enrolled}.
    """
    enrolled = 0
    already_enrolled = 0

    for email in student_emails:
        email = email.strip().lower()
        if not email:
            continue

        # Check if already linked to an active student
        existing = await conn.fetchrow(
            "SELECT enrolment_id, status FROM school_enrolments WHERE school_id = $1 AND student_email = $2",
            uuid.UUID(school_id), email,
        )
        if existing:
            already_enrolled += 1
            continue

        # Check if this student is already registered
        student_row = await conn.fetchrow(
            "SELECT student_id FROM students WHERE email = $1",
            email,
        )
        student_id = student_row["student_id"] if student_row else None
        status = "active" if student_id else "pending"

        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (school_id, student_email) DO NOTHING
            """,
            uuid.UUID(school_id), email,
            student_id,
            status,
        )

        # If student is already registered, also update students.school_id
        if student_id:
            await conn.execute(
                """
                UPDATE students
                SET school_id = $1, enrolled_at = NOW()
                WHERE student_id = $2 AND school_id IS NULL
                """,
                uuid.UUID(school_id), student_id,
            )

        enrolled += 1

    log.info("roster_uploaded", school_id=school_id, enrolled=enrolled, already_enrolled=already_enrolled)
    return {"enrolled": enrolled, "already_enrolled": already_enrolled}


async def get_roster(
    conn: asyncpg.Connection,
    school_id: str,
) -> list:
    """Return all enrolment rows for a school, ordered by added_at descending."""
    rows = await conn.fetch(
        """
        SELECT student_email, student_id::text, status, added_at
        FROM school_enrolments
        WHERE school_id = $1
        ORDER BY added_at DESC
        """,
        uuid.UUID(school_id),
    )
    return [dict(r) for r in rows]


async def link_student(
    conn: asyncpg.Connection,
    student_id: str,
    email: str,
) -> Optional[str]:
    """
    After student login/registration, check for a pending enrolment by email.

    If found:
      - Sets school_enrolments.student_id and status='active'
      - Sets students.school_id and enrolled_at

    Returns the school_id that was linked, or None if no pending enrolment found.
    """
    email = email.strip().lower()
    row = await conn.fetchrow(
        """
        SELECT enrolment_id, school_id::text
        FROM school_enrolments
        WHERE student_email = $1 AND status = 'pending'
        ORDER BY added_at
        LIMIT 1
        """,
        email,
    )
    if not row:
        return None

    enrolment_id = row["enrolment_id"]
    school_id = row["school_id"]

    await conn.execute(
        """
        UPDATE school_enrolments
        SET student_id = $1, status = 'active'
        WHERE enrolment_id = $2
        """,
        uuid.UUID(student_id), enrolment_id,
    )

    await conn.execute(
        """
        UPDATE students
        SET school_id = $1, enrolled_at = NOW()
        WHERE student_id = $2 AND school_id IS NULL
        """,
        uuid.UUID(school_id), uuid.UUID(student_id),
    )

    log.info("student_enrolled", student_id=student_id, school_id=school_id)
    return school_id
