"""
seed_phase_a_dev.py — Seed two dev schools for local development and testing.

Dev School A — primary school used to author teacher overrides.
Dev School B — secondary school used to verify content is school-scoped
               (School B students must never see School A overrides and vice versa).

Both schools use Phase A local auth (email + password).

Idempotent: safe to run multiple times. Existing rows are left unchanged.
Use --reset to drop and recreate all dev school data (destructive).

Usage:
    docker compose exec api python scripts/seed_phase_a_dev.py
    docker compose exec api python scripts/seed_phase_a_dev.py --reset
"""

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

# ── School A ──────────────────────────────────────────────────────────────────

SCHOOL_A = {
    "school_id": "d0000000-0000-0000-0000-000000000001",
    "name": "Dev School",
    "country": "US",
    "contact_email": "admin@devschool.dev",
}

SCHOOL_A_ADMIN = {
    "teacher_id": "d0000000-0000-0000-0000-000000000010",
    "name": "Dev Admin",
    "email": "admin@devschool.dev",
    "password": os.environ.get("PHASE_A_SCHOOL_A_ADMIN_PASSWORD", "DevAdmin1234!"),
    "role": "school_admin",
}

SCHOOL_A_TEACHER = {
    "teacher_id": "d0000000-0000-0000-0000-000000000011",
    "name": "Dev Teacher",
    "email": "teacher@devschool.dev",
    "password": "DevTeacher1234!",
    "role": "teacher",
}

SCHOOL_A_STUDENT = {
    "student_id": "d0000000-0000-0000-0000-000000000020",
    "name": "Dev Student",
    "email": "student@devschool.dev",
    "password": "DevStudent1234!",
    "grade": 8,
}

# ── School B ──────────────────────────────────────────────────────────────────
# Used to verify that School A overrides are NOT served to School B students
# and that School B can maintain its own independent set of overrides.

SCHOOL_B = {
    "school_id": "d0000000-0000-0000-0000-000000000002",
    "name": "Dev School B",
    "country": "US",
    "contact_email": "admin@devschoolb.dev",
}

SCHOOL_B_ADMIN = {
    "teacher_id": "d0000000-0000-0000-0000-000000000030",
    "name": "Dev Admin B",
    "email": "admin@devschoolb.dev",
    "password": os.environ.get("PHASE_A_SCHOOL_B_ADMIN_PASSWORD", "DevAdminB1234!"),
    "role": "school_admin",
}

SCHOOL_B_TEACHER = {
    "teacher_id": "d0000000-0000-0000-0000-000000000031",
    "name": "Dev Teacher B",
    "email": "teacher@devschoolb.dev",
    "password": "DevTeacherB1234!",
    "role": "teacher",
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


async def _seed_school(conn, school: dict, teachers: list[dict], students: list[dict]) -> None:
    existing = await conn.fetchrow(
        "SELECT school_id FROM schools WHERE school_id = $1", school["school_id"]
    )
    if existing:
        print(f"  School already exists — skipping: {school['name']}")
    else:
        await conn.execute(
            """
            INSERT INTO schools (school_id, name, country, contact_email, status)
            VALUES ($1, $2, $3, $4, 'active')
            """,
            school["school_id"],
            school["name"],
            school["country"],
            school["contact_email"],
        )
        print(f"  Created school: {school['name']}")

    for t in teachers:
        existing = await conn.fetchrow(
            "SELECT teacher_id FROM teachers WHERE email = $1", t["email"]
        )
        if existing:
            print(f"  Teacher already exists — skipping: {t['email']}")
        else:
            await conn.execute(
                """
                INSERT INTO teachers
                    (teacher_id, school_id, name, email, role,
                     auth_provider, external_auth_id,
                     password_hash, first_login, account_status)
                VALUES ($1, $2, $3, $4, $5, 'local', $6, $7, false, 'active')
                """,
                t["teacher_id"],
                school["school_id"],
                t["name"],
                t["email"],
                t["role"],
                f"local:{t['teacher_id']}",
                _hash(t["password"]),
            )
            print(f"  Created teacher ({t['role']}): {t['email']}")

    for s in students:
        existing = await conn.fetchrow(
            "SELECT student_id FROM students WHERE email = $1", s["email"]
        )
        if existing:
            print(f"  Student already exists — skipping: {s['email']}")
        else:
            await conn.execute(
                """
                INSERT INTO students
                    (student_id, school_id, name, email, grade,
                     auth_provider, external_auth_id,
                     password_hash, first_login, account_status)
                VALUES ($1, $2, $3, $4, $5, 'local', $6, $7, false, 'active')
                """,
                s["student_id"],
                school["school_id"],
                s["name"],
                s["email"],
                s["grade"],
                f"local:{s['student_id']}",
                _hash(s["password"]),
            )
            print(f"  Created student (grade {s['grade']}): {s['email']}")


async def _seed(reset: bool) -> None:
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    try:
        if reset:
            print("Removing existing dev school data…")
            for school in (SCHOOL_A, SCHOOL_B):
                sid = school["school_id"]
                await conn.execute("DELETE FROM students WHERE school_id = $1", sid)
                await conn.execute("DELETE FROM teachers WHERE school_id = $1", sid)
                await conn.execute("DELETE FROM schools WHERE school_id = $1", sid)
            print("Removed.\n")

        print("── School A ─────────────────────────────────────────")
        await _seed_school(
            conn,
            SCHOOL_A,
            teachers=[SCHOOL_A_ADMIN, SCHOOL_A_TEACHER],
            students=[SCHOOL_A_STUDENT],
        )

        print("\n── School B ─────────────────────────────────────────")
        await _seed_school(
            conn,
            SCHOOL_B,
            teachers=[SCHOOL_B_ADMIN, SCHOOL_B_TEACHER],
            students=[SCHOOL_B_STUDENT],
        )

    finally:
        await conn.close()

    _print_summary()


def _print_summary() -> None:
    divider = "─" * 60

    def _block(label: str, school: dict, admin: dict, teacher: dict, student: dict) -> None:
        print(f"\n{divider}")
        print(f"  {label} — {school['name']}")
        print(divider)
        print("  Login URL : http://localhost:3000/signin")
        print()
        print("  School Admin")
        print(f"    email    : {admin['email']}")
        print(f"    password : {admin['password']}")
        print()
        print("  Teacher")
        print(f"    email    : {teacher['email']}")
        print(f"    password : {teacher['password']}")
        print()
        print(f"  Student  (grade {student['grade']})")
        print(f"    email    : {student['email']}")
        print(f"    password : {student['password']}")

    _block("School A", SCHOOL_A, SCHOOL_A_ADMIN, SCHOOL_A_TEACHER, SCHOOL_A_STUDENT)
    _block("School B", SCHOOL_B, SCHOOL_B_ADMIN, SCHOOL_B_TEACHER, SCHOOL_B_STUDENT)
    print(f"\n{divider}")
    print("  Isolation test: adopt the same OOB curriculum in both schools,")
    print("  publish different overrides for each, then verify each student")
    print("  only sees their own school's content.")
    print(divider)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dev school data (Schools A and B).")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all dev school data (destructive).",
    )
    args = parser.parse_args()
    asyncio.run(_seed(args.reset))


if __name__ == "__main__":
    main()
