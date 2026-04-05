"""
backend/src/school/enrolment_service.py

School enrolment and student-teacher assignment business logic.

Functions:
  upload_roster             — school_admin uploads student list with grade + teacher
  get_roster                — fetch all enrolment rows for a school
  link_student              — called on student login; links student_id to pending enrolment
  assign_student            — set or replace a student's grade + teacher assignment
  get_student_assignment    — fetch current teacher assignment for a student
  reassign_students_bulk    — move all students from one teacher to another (e.g. teacher leaves)
"""

from __future__ import annotations

import uuid

import asyncpg

from src.utils.logger import get_logger

log = get_logger("enrolment")


# ── Roster upload ─────────────────────────────────────────────────────────────


async def upload_roster(
    conn: asyncpg.Connection,
    school_id: str,
    entries: list[dict],  # [{email, grade?, teacher_id?}]
) -> dict:
    """
    Upsert enrolment rows for the given student list.

    Each entry must have an 'email'. 'grade' and 'teacher_id' are optional at
    enrolment time — they can be set later via assign_student(). When provided,
    a student_teacher_assignments row is also created/replaced.

    Returns {enrolled, already_enrolled, errors: [{email, reason}]}.
    """
    enrolled = 0
    already_enrolled = 0
    errors: list[dict] = []

    sid = uuid.UUID(school_id)

    for entry in entries:
        email = entry.get("email", "").strip().lower()
        if not email:
            continue

        grade: int | None = entry.get("grade")
        teacher_id_raw: str | None = entry.get("teacher_id")

        # Validate teacher belongs to this school when provided
        if teacher_id_raw:
            try:
                tid = uuid.UUID(teacher_id_raw)
            except ValueError:
                errors.append({"email": email, "reason": "invalid teacher_id format"})
                continue

            teacher_ok = await conn.fetchval(
                "SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $2",
                tid, sid,
            )
            if not teacher_ok:
                errors.append({"email": email, "reason": "teacher not found in this school"})
                continue

            # Teacher must be assigned to the requested grade
            if grade:
                grade_ok = await conn.fetchval(
                    """
                    SELECT 1 FROM teacher_grade_assignments
                    WHERE teacher_id = $1 AND grade = $2
                    """,
                    tid, grade,
                )
                if not grade_ok:
                    errors.append({
                        "email": email,
                        "reason": f"teacher is not assigned to grade {grade}",
                    })
                    continue
        else:
            tid = None

        # Check if already enrolled
        existing = await conn.fetchrow(
            "SELECT enrolment_id, status FROM school_enrolments "
            "WHERE school_id = $1 AND student_email = $2",
            sid, email,
        )
        if existing:
            already_enrolled += 1
            # If grade/teacher provided, still update the assignment
            if grade and tid:
                student_row = await conn.fetchrow(
                    "SELECT student_id FROM students WHERE email = $1", email
                )
                if student_row:
                    await assign_student(
                        conn, school_id, str(student_row["student_id"]),
                        grade, str(tid), assigned_by=None,
                    )
            continue

        # Resolve existing student account
        student_row = await conn.fetchrow(
            "SELECT student_id FROM students WHERE email = $1", email
        )
        student_id = student_row["student_id"] if student_row else None
        status = "active" if student_id else "pending"

        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_email, student_id, status, grade, teacher_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (school_id, student_email) DO NOTHING
            """,
            sid, email, student_id, status, grade, tid,
        )

        # Link student → school
        if student_id:
            await conn.execute(
                """
                UPDATE students
                SET school_id = $1, enrolled_at = NOW()
                WHERE student_id = $2 AND school_id IS NULL
                """,
                sid, student_id,
            )
            # Create assignment if grade+teacher provided
            if grade and tid:
                await assign_student(
                    conn, school_id, str(student_id),
                    grade, str(tid), assigned_by=None,
                )

        enrolled += 1

    log.info(
        "roster_uploaded",
        school_id=school_id,
        enrolled=enrolled,
        already_enrolled=already_enrolled,
        errors=len(errors),
    )
    return {"enrolled": enrolled, "already_enrolled": already_enrolled, "errors": errors}


# ── Roster read ───────────────────────────────────────────────────────────────


async def get_roster(
    conn: asyncpg.Connection,
    school_id: str,
) -> list:
    """
    Return all enrolment rows for a school, joined with current teacher assignment.
    """
    rows = await conn.fetch(
        """
        SELECT
            se.student_email,
            se.student_id::text,
            se.status,
            se.grade            AS enrolled_grade,
            se.added_at,
            sta.teacher_id::text AS assigned_teacher_id,
            t.name              AS assigned_teacher_name,
            sta.grade           AS assigned_grade
        FROM school_enrolments se
        LEFT JOIN student_teacher_assignments sta
            ON sta.student_id = se.student_id
        LEFT JOIN teachers t
            ON t.teacher_id = sta.teacher_id
        WHERE se.school_id = $1
        ORDER BY se.added_at DESC
        """,
        uuid.UUID(school_id),
    )
    return [dict(r) for r in rows]


# ── Student linking on first login ────────────────────────────────────────────


async def link_student(
    conn: asyncpg.Connection,
    student_id: str,
    email: str,
) -> str | None:
    """
    After student Auth0 login, check for a pending enrolment by email.

    If found:
      - Links student_id to the enrolment row (status → active)
      - Sets students.school_id + enrolled_at
      - Sets students.grade from enrolment grade (school authority wins)
      - Creates student_teacher_assignments row if teacher_id was set at enrolment

    Returns the school_id linked, or None.
    """
    email = email.strip().lower()
    row = await conn.fetchrow(
        """
        SELECT enrolment_id, school_id::text, grade, teacher_id::text
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
    grade: int | None = row["grade"]
    teacher_id: str | None = row["teacher_id"]

    await conn.execute(
        """
        UPDATE school_enrolments
        SET student_id = $1, status = 'active'
        WHERE enrolment_id = $2
        """,
        uuid.UUID(student_id), enrolment_id,
    )

    # Update students row — school is the authority on grade
    update_fields = "school_id = $1, enrolled_at = NOW()"
    params: list = [uuid.UUID(school_id)]
    if grade:
        update_fields += f", grade = ${len(params) + 1}"
        params.append(grade)
    params.append(uuid.UUID(student_id))

    await conn.execute(
        f"""
        UPDATE students SET {update_fields}
        WHERE student_id = ${len(params)} AND school_id IS NULL
        """,
        *params,
    )

    # Create teacher assignment if present on enrolment
    if grade and teacher_id:
        await assign_student(
            conn, school_id, student_id, grade, teacher_id, assigned_by=None
        )

    log.info("student_enrolled", student_id=student_id, school_id=school_id, grade=grade)
    return school_id


# ── Student-teacher assignment ────────────────────────────────────────────────


async def assign_student(
    conn: asyncpg.Connection,
    school_id: str,
    student_id: str,
    grade: int,
    teacher_id: str,
    assigned_by: str | None,
) -> dict:
    """
    Set or replace a student's grade+teacher assignment.

    The UNIQUE (student_id, grade) constraint means a student can only be in
    one teacher's class per grade. ON CONFLICT replaces the teacher.

    Rules:
      - Teacher must belong to this school.
      - Teacher must be assigned to this grade (teacher_grade_assignments).
      - Student must be enrolled in this school.

    Raises ValueError with a descriptive message on any violation.
    Returns the new assignment row as a dict.
    """
    sid = uuid.UUID(school_id)
    stud = uuid.UUID(student_id)
    tid = uuid.UUID(teacher_id)

    # Student must be enrolled in this school
    enrolled = await conn.fetchval(
        "SELECT 1 FROM school_enrolments WHERE school_id = $1 AND student_id = $2",
        sid, stud,
    )
    if not enrolled:
        raise ValueError("student is not enrolled in this school")

    # Teacher must belong to this school
    teacher_ok = await conn.fetchval(
        "SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $2",
        tid, sid,
    )
    if not teacher_ok:
        raise ValueError("teacher does not belong to this school")

    # Teacher must be assigned to the grade
    grade_ok = await conn.fetchval(
        "SELECT 1 FROM teacher_grade_assignments WHERE teacher_id = $1 AND grade = $2",
        tid, grade,
    )
    if not grade_ok:
        raise ValueError(f"teacher is not assigned to grade {grade}")

    assigned_by_id = uuid.UUID(assigned_by) if assigned_by else None

    row = await conn.fetchrow(
        """
        INSERT INTO student_teacher_assignments
            (student_id, teacher_id, school_id, grade, assigned_by)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (student_id, grade)
            DO UPDATE SET
                teacher_id  = EXCLUDED.teacher_id,
                assigned_at = NOW(),
                assigned_by = EXCLUDED.assigned_by
        RETURNING
            assignment_id::text,
            student_id::text,
            teacher_id::text,
            school_id::text,
            grade,
            assigned_at
        """,
        stud, tid, sid, grade, assigned_by_id,
    )

    # Keep students.grade in sync — school is the authority
    await conn.execute(
        "UPDATE students SET grade = $1 WHERE student_id = $2",
        grade, stud,
    )

    log.info(
        "student_assigned",
        student_id=student_id,
        teacher_id=teacher_id,
        grade=grade,
        school_id=school_id,
    )
    return dict(row)


async def get_student_assignment(
    conn: asyncpg.Connection,
    school_id: str,
    student_id: str,
) -> dict | None:
    """Return the current teacher assignment for a student, or None."""
    row = await conn.fetchrow(
        """
        SELECT
            sta.assignment_id::text,
            sta.student_id::text,
            sta.teacher_id::text,
            t.name      AS teacher_name,
            t.email     AS teacher_email,
            sta.school_id::text,
            sta.grade,
            sta.assigned_at,
            ab.name     AS assigned_by_name
        FROM student_teacher_assignments sta
        JOIN teachers t  ON t.teacher_id  = sta.teacher_id
        LEFT JOIN teachers ab ON ab.teacher_id = sta.assigned_by
        WHERE sta.school_id = $1 AND sta.student_id = $2
        """,
        uuid.UUID(school_id),
        uuid.UUID(student_id),
    )
    return dict(row) if row else None


async def reassign_students_bulk(
    conn: asyncpg.Connection,
    school_id: str,
    from_teacher_id: str,
    to_teacher_id: str,
    grade: int,
    assigned_by: str,
) -> int:
    """
    Move all students assigned to from_teacher in a given grade to to_teacher.
    Used when a teacher leaves or a class is restructured.

    Returns the number of students reassigned.
    """
    sid = uuid.UUID(school_id)
    from_tid = uuid.UUID(from_teacher_id)
    to_tid = uuid.UUID(to_teacher_id)
    by_id = uuid.UUID(assigned_by)

    # to_teacher must be in this school and assigned to this grade
    to_ok = await conn.fetchval(
        """
        SELECT 1 FROM teacher_grade_assignments
        WHERE teacher_id = $1 AND grade = $2
          AND EXISTS (SELECT 1 FROM teachers WHERE teacher_id = $1 AND school_id = $3)
        """,
        to_tid, grade, sid,
    )
    if not to_ok:
        raise ValueError("destination teacher not found or not assigned to this grade")

    result = await conn.execute(
        """
        UPDATE student_teacher_assignments
        SET teacher_id  = $1,
            assigned_at = NOW(),
            assigned_by = $2
        WHERE school_id   = $3
          AND teacher_id  = $4
          AND grade       = $5
        """,
        to_tid, by_id, sid, from_tid, grade,
    )

    # Parse "UPDATE N" string
    count = int(result.split()[-1])
    log.info(
        "students_bulk_reassigned",
        school_id=school_id,
        from_teacher=from_teacher_id,
        to_teacher=to_teacher_id,
        grade=grade,
        count=count,
    )
    return count
