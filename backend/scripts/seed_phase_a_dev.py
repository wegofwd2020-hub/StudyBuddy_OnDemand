"""
seed_phase_a_dev.py — Create a Dev School with one teacher and one student
using Phase A local auth (email + password), for local development and demos.

Idempotent: safe to run multiple times. Existing users are left unchanged.
Use --reset to drop and recreate the dev school (destructive).

Usage:
    docker compose exec api python scripts/seed_phase_a_dev.py
    docker compose exec api python scripts/seed_phase_a_dev.py --reset
"""

import argparse
import asyncio
import os
import sys
import uuid

import bcrypt

# Ensure the backend src/ tree is importable when run from the container.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy",
)

DEV_SCHOOL = {
    "school_id": "d0000000-0000-0000-0000-000000000001",
    "name": "Dev School",
    "country": "US",
    "contact_email": "admin@devschool.local",
}

DEV_ADMIN = {
    "teacher_id": "d0000000-0000-0000-0000-000000000010",
    "name": "Dev Admin",
    "email": "admin@devschool.local",
    "password": "DevAdmin1234!",
    "role": "school_admin",
}

DEV_TEACHER = {
    "teacher_id": "d0000000-0000-0000-0000-000000000011",
    "name": "Dev Teacher",
    "email": "teacher@devschool.local",
    "password": "DevTeacher1234!",
    "role": "teacher",
}

DEV_STUDENT = {
    "student_id": "d0000000-0000-0000-0000-000000000020",
    "name": "Dev Student",
    "email": "student@devschool.local",
    "password": "DevStudent1234!",
    "grade": 8,
}


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def _seed(reset: bool) -> None:
    conn = await asyncpg.connect(DB_URL)

    # Bypass RLS for seed operations — this connection acts as a privileged admin.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    try:
        if reset:
            print("Removing existing dev school data…")
            sid = DEV_SCHOOL["school_id"]
            await conn.execute("DELETE FROM students WHERE school_id = $1", sid)
            await conn.execute("DELETE FROM teachers WHERE school_id = $1", sid)
            await conn.execute("DELETE FROM schools WHERE school_id = $1", sid)
            print("Removed.")

        # ── School ────────────────────────────────────────────────────────────
        existing_school = await conn.fetchrow(
            "SELECT school_id FROM schools WHERE school_id = $1",
            DEV_SCHOOL["school_id"],
        )
        if existing_school:
            print(f"School already exists — skipping create: {DEV_SCHOOL['name']}")
        else:
            await conn.execute(
                """
                INSERT INTO schools (school_id, name, country, contact_email, account_status)
                VALUES ($1, $2, $3, $4, 'active')
                """,
                DEV_SCHOOL["school_id"],
                DEV_SCHOOL["name"],
                DEV_SCHOOL["country"],
                DEV_SCHOOL["contact_email"],
            )
            print(f"Created school: {DEV_SCHOOL['name']}")

        # ── School admin ──────────────────────────────────────────────────────
        for t in (DEV_ADMIN, DEV_TEACHER):
            existing = await conn.fetchrow(
                "SELECT teacher_id FROM teachers WHERE email = $1", t["email"]
            )
            if existing:
                print(f"Teacher already exists — skipping: {t['email']}")
            else:
                await conn.execute(
                    """
                    INSERT INTO teachers
                        (teacher_id, school_id, name, email, role,
                         auth_provider, password_hash, first_login, account_status)
                    VALUES ($1, $2, $3, $4, $5, 'local', $6, false, 'active')
                    """,
                    t["teacher_id"],
                    DEV_SCHOOL["school_id"],
                    t["name"],
                    t["email"],
                    t["role"],
                    _hash(t["password"]),
                )
                print(f"Created teacher ({t['role']}): {t['email']}")

        # ── Student ───────────────────────────────────────────────────────────
        s = DEV_STUDENT
        existing = await conn.fetchrow(
            "SELECT student_id FROM students WHERE email = $1", s["email"]
        )
        if existing:
            print(f"Student already exists — skipping: {s['email']}")
        else:
            await conn.execute(
                """
                INSERT INTO students
                    (student_id, school_id, name, email, grade,
                     auth_provider, password_hash, first_login, account_status)
                VALUES ($1, $2, $3, $4, $5, 'local', $6, false, 'active')
                """,
                s["student_id"],
                DEV_SCHOOL["school_id"],
                s["name"],
                s["email"],
                s["grade"],
                _hash(s["password"]),
            )
            print(f"Created student: {s['email']}")

    finally:
        await conn.close()

    print()
    print("─" * 55)
    print("Dev School — Phase A credentials")
    print("─" * 55)
    print(f"  Login URL : http://localhost:3000/school/login")
    print()
    print(f"  School Admin")
    print(f"    email    : {DEV_ADMIN['email']}")
    print(f"    password : {DEV_ADMIN['password']}")
    print()
    print(f"  Teacher")
    print(f"    email    : {DEV_TEACHER['email']}")
    print(f"    password : {DEV_TEACHER['password']}")
    print()
    print(f"  Student")
    print(f"    email    : {DEV_STUDENT['email']}")
    print(f"    password : {DEV_STUDENT['password']}")
    print("─" * 55)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Phase A dev school data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all dev school data (destructive).",
    )
    args = parser.parse_args()
    asyncio.run(_seed(args.reset))


if __name__ == "__main__":
    main()
