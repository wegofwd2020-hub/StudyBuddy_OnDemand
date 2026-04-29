"""
reset_dev_data.py — Hard-reset classrooms, students, and school forks for
Dev Schools A and B.

Keeps:
  - Schools (A and B) and their teachers
  - All platform OOB curricula and generated content files
  - Admin accounts

Removes:
  - All classrooms + packages + student assignments
  - All grade-to-curriculum assignments for dev schools
  - All library adoptions (school_adopted_curricula)
  - All school-fork curricula rows (owner_type='school')
  - All teacher content overrides (unit_content_overrides / active_versions)
  - All students and cascaded rows (student_teacher_assignments, entitlements)
  - All enrolment records for dev schools

Then re-seeds fresh dev students so login credentials are immediately usable.

Usage:
    docker compose exec api python scripts/reset_dev_data.py
    docker compose exec api python scripts/reset_dev_data.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy",
)

# ── Dev school IDs (must match seed_phase_a_dev.py) ───────────────────────────

SCHOOL_A_ID = "d0000000-0000-0000-0000-000000000001"
SCHOOL_B_ID = "d0000000-0000-0000-0000-000000000002"

DEV_SCHOOL_IDS = [SCHOOL_A_ID, SCHOOL_B_ID]

# ── Dev student definitions (same as seed_phase_a_dev.py) ────────────────────

SCHOOL_A_STUDENT = {
    "student_id": "d0000000-0000-0000-0000-000000000020",
    "name": "Dev Student",
    "email": "student@devschool.dev",
    "password": "DevStudent1234!",
    "grade": 8,
}

SCHOOL_B_STUDENT = {
    "student_id": "d0000000-0000-0000-0000-000000000040",
    "name": "Dev Student B",
    "email": "student@devschoolb.dev",
    "password": "DevStudentB1234!",
    "grade": 8,
}


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


# ── Table-by-table cleanup ────────────────────────────────────────────────────


async def _reset(conn, dry_run: bool) -> None:
    def _run(label: str, query: str, *args):
        if dry_run:
            print(f"  [dry-run] {label}")
            return None
        return conn.execute(query, *args)

    async def run(label: str, query: str, *args):
        if dry_run:
            print(f"  [dry-run] {label}")
            return
        result = await conn.execute(query, *args)
        print(f"  {label} — {result}")

    # ── 1. Teacher content overrides ──────────────────────────────────────────
    print("\n── Teacher content overrides ────────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE unit_content_active_versions (school {sid[:8]}…)",
            "DELETE FROM unit_content_active_versions WHERE school_id = $1",
            sid,
        )
        await run(
            f"DELETE unit_content_overrides (school {sid[:8]}…)",
            "DELETE FROM unit_content_overrides WHERE school_id = $1",
            sid,
        )

    # ── 2. Classrooms (cascade to classroom_packages + classroom_students) ───
    print("\n── Classrooms ───────────────────────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE classrooms (school {sid[:8]}…)",
            "DELETE FROM classrooms WHERE school_id = $1",
            sid,
        )

    # ── 3. Grade-curriculum assignments (RESTRICT FK — must precede curricula)
    print("\n── Grade-curriculum assignments ─────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE grade_curriculum_assignments (school {sid[:8]}…)",
            "DELETE FROM grade_curriculum_assignments WHERE school_id = $1",
            sid,
        )

    # ── 4. Library adoptions ──────────────────────────────────────────────────
    print("\n── Library adoptions ────────────────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE school_adopted_curricula (school {sid[:8]}…)",
            "DELETE FROM school_adopted_curricula WHERE school_id = $1",
            sid,
        )

    # ── 5. School-fork curricula (owner_type='school' only — OOB is safe) ────
    print("\n── School fork curricula ────────────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE fork curricula (school {sid[:8]}…)",
            "DELETE FROM curricula WHERE school_id = $1 AND owner_type = 'school'",
            sid,
        )

    # ── 6. Students + cascaded rows ───────────────────────────────────────────
    # student_teacher_assignments.student_id → ON DELETE CASCADE (auto-removed)
    # student_entitlements has no FK cascade — delete first
    print("\n── Students and linked rows ─────────────────────────────────────────")
    for sid in DEV_SCHOOL_IDS:
        await run(
            f"DELETE student_entitlements (school {sid[:8]}…)",
            """
            DELETE FROM student_entitlements
            WHERE student_id IN (
                SELECT student_id FROM students WHERE school_id = $1
            )
            """,
            sid,
        )
        await run(
            f"DELETE school_enrolments (school {sid[:8]}…)",
            "DELETE FROM school_enrolments WHERE school_id = $1",
            sid,
        )
        await run(
            f"DELETE students (school {sid[:8]}…)",
            "DELETE FROM students WHERE school_id = $1",
            sid,
        )

    # ── 7. Re-seed fresh students ─────────────────────────────────────────────
    if dry_run:
        print("\n── [dry-run] Would re-seed dev students")
        return

    print("\n── Re-seeding dev students ──────────────────────────────────────────")
    for school_id, student in [
        (SCHOOL_A_ID, SCHOOL_A_STUDENT),
        (SCHOOL_B_ID, SCHOOL_B_STUDENT),
    ]:
        await conn.execute(
            """
            INSERT INTO students
                (student_id, school_id, name, email, grade,
                 auth_provider, external_auth_id,
                 password_hash, first_login, account_status)
            VALUES ($1, $2, $3, $4, $5, 'local', $6, $7, false, 'active')
            ON CONFLICT (student_id) DO NOTHING
            """,
            student["student_id"],
            school_id,
            student["name"],
            student["email"],
            student["grade"],
            f"local:{student['student_id']}",
            _hash(student["password"]),
        )
        print(f"  Seeded student: {student['email']} (grade {student['grade']})")


async def main(dry_run: bool) -> None:
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    try:
        print(f"{'[DRY RUN] ' if dry_run else ''}Resetting dev school data…")
        print(f"  Schools in scope: {', '.join(DEV_SCHOOL_IDS)}")
        await _reset(conn, dry_run)
    finally:
        await conn.close()

    if not dry_run:
        _print_summary()


def _print_summary() -> None:
    print("\n" + "─" * 60)
    print("  Reset complete. Fresh student credentials:")
    print("─" * 60)
    print()
    print("  School A student")
    print(f"    email    : {SCHOOL_A_STUDENT['email']}")
    print(f"    password : {SCHOOL_A_STUDENT['password']}")
    print()
    print("  School B student")
    print(f"    email    : {SCHOOL_B_STUDENT['email']}")
    print(f"    password : {SCHOOL_B_STUDENT['password']}")
    print()
    print("  Teachers and admins are unchanged.")
    print("  Platform OOB curricula are unchanged.")
    print("─" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hard-reset dev school classrooms/students/forks."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without touching the DB.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
