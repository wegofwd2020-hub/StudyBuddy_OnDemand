#!/usr/bin/env python3
"""
backend/scripts/seed_demo_milfordwaterford.py

Creates (or refreshes) a full demo school environment for MilfordWaterford
Local School — used for manual QA, product demos, and investor showcases.

Accounts created
────────────────
  School   : MilfordWaterford Local School

  Teachers (login via POST /demo/teacher/auth/login):
    sam.houston@milfordwaterford.edu   / MWTeacher-Sam-2026!
    linda.ronstad@milfordwaterford.edu / MWTeacher-Linda-2026!

  Students (login via POST /demo/auth/login):
    samjr@milfordwaterford.edu         / MWStudent-SamJr-2026!    Grade 8
    jose.herbert@milfordwaterford.edu  / MWStudent-Jose-2026!     Grade 8
    samsr@milfordwaterford.edu         / MWStudent-SamSr-2026!    Grade 12
    linda.herbert@milfordwaterford.edu / MWStudent-Linda-2026!    Grade 12

All accounts expire 2099-12-31 (effectively non-expiring).

Idempotency
───────────
The script is fully idempotent — safe to re-run on any environment.
  - Existing rows are updated in-place (password hash refreshed).
  - Nothing is duplicated.
  - Use --dry-run to preview without touching the database.

Usage (inside the api container):
    python scripts/seed_demo_milfordwaterford.py

From the repo root:
    docker compose exec api python scripts/seed_demo_milfordwaterford.py

Options:
    --dry-run    Print what would happen without writing to the DB
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime

import asyncpg
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Constants ──────────────────────────────────────────────────────────────────

SCHOOL_NAME = "MilfordWaterford Local School"
SCHOOL_EMAIL = "admin@milfordwaterford.edu"
SCHOOL_COUNTRY = "CA"

# Accounts never expire for demo purposes
NEVER_EXPIRES = datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC)

TEACHERS: list[dict] = [
    {
        "name": "Sam Houston",
        "email": "sam.houston@milfordwaterford.edu",
        "password": "MWTeacher-Sam-2026!",
        "role": "teacher",
    },
    {
        "name": "Linda Ronstad",
        "email": "linda.ronstad@milfordwaterford.edu",
        "password": "MWTeacher-Linda-2026!",
        "role": "teacher",
    },
]

STUDENTS: list[dict] = [
    {
        "name": "Sam Jr",
        "email": "samjr@milfordwaterford.edu",
        "password": "MWStudent-SamJr-2026!",
        "grade": 8,
    },
    {
        "name": "Jose Herbert",
        "email": "jose.herbert@milfordwaterford.edu",
        "password": "MWStudent-Jose-2026!",
        "grade": 8,
    },
    {
        "name": "Sam Sr",
        "email": "samsr@milfordwaterford.edu",
        "password": "MWStudent-SamSr-2026!",
        "grade": 12,
    },
    {
        "name": "Linda Herbert",
        "email": "linda.herbert@milfordwaterford.edu",
        "password": "MWStudent-Linda-2026!",
        "grade": 12,
    },
]

_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
DATABASE_URL = _raw_url.replace("@pgbouncer:", "@db:")


# ── Helpers ────────────────────────────────────────────────────────────────────


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _col(label: str, value: object, width: int = 26) -> str:
    return f"  {label:<{width}}: {value}"


# ── School ─────────────────────────────────────────────────────────────────────


async def _upsert_school(conn: asyncpg.Connection) -> str:
    """Return school_id, creating the row if it doesn't already exist."""
    existing = await conn.fetchval(
        "SELECT school_id FROM schools WHERE name = $1", SCHOOL_NAME
    )
    if existing:
        return str(existing)

    school_id = await conn.fetchval(
        """
        INSERT INTO schools (name, contact_email, country, status)
        VALUES ($1, $2, $3, 'active')
        RETURNING school_id
        """,
        SCHOOL_NAME,
        SCHOOL_EMAIL,
        SCHOOL_COUNTRY,
    )
    return str(school_id)


# ── Teachers ───────────────────────────────────────────────────────────────────


async def _upsert_teacher(
    conn: asyncpg.Connection,
    school_id: str,
    teacher: dict,
) -> dict:
    """
    Upsert a demo teacher:
      teachers row  (auth_provider='demo', school_id=school_id)
      demo_teacher_requests row (status='verified')
      demo_teacher_accounts row (non-expiring)

    Returns a summary dict for the final report.
    """
    email = teacher["email"]
    name = teacher["name"]
    password = teacher["password"]
    password_hash = _hash(password)

    # ── Check if demo_teacher_accounts row already exists ──────────────────────
    existing_account = await conn.fetchrow(
        """
        SELECT dta.id, dta.teacher_id
        FROM demo_teacher_accounts dta
        WHERE dta.email = $1
        """,
        email,
    )

    if existing_account:
        # Refresh password + extend expiry
        await conn.execute(
            """
            UPDATE demo_teacher_accounts
               SET password_hash = $1,
                   expires_at    = $2,
                   revoked_at    = NULL,
                   revoked_by    = NULL,
                   extended_at   = NOW()
             WHERE email = $3
            """,
            password_hash,
            NEVER_EXPIRES,
            email,
        )
        # Ensure teacher row has the correct school_id
        await conn.execute(
            """
            UPDATE teachers SET school_id = $1 WHERE teacher_id = $2
            """,
            school_id,
            existing_account["teacher_id"],
        )
        return {
            "name": name,
            "email": email,
            "password": password,
            "teacher_id": str(existing_account["teacher_id"]),
            "account_id": str(existing_account["id"]),
            "action": "refreshed",
        }

    # ── Fresh create ───────────────────────────────────────────────────────────

    # demo_teacher_requests (seed placeholder — no real IP/UA)
    request_id = await conn.fetchval(
        """
        INSERT INTO demo_teacher_requests (email, ip_address, user_agent, status)
        VALUES ($1, 'seed-script', 'seed_demo_milfordwaterford.py', 'verified')
        RETURNING id
        """,
        email,
    )

    # teachers row — with real school_id so JWT will include it on login
    demo_external_id = f"demo_teacher:{request_id}"
    teacher_id = await conn.fetchval(
        """
        INSERT INTO teachers
            (school_id, external_auth_id, auth_provider, name, email,
             role, account_status)
        VALUES ($1, $2, 'demo', $3, $4, $5, 'active')
        ON CONFLICT (email) DO UPDATE
            SET school_id = EXCLUDED.school_id,
                name      = EXCLUDED.name
        RETURNING teacher_id
        """,
        school_id,
        demo_external_id,
        name,
        email,
        teacher["role"],
    )

    # demo_teacher_accounts
    account_id = await conn.fetchval(
        """
        INSERT INTO demo_teacher_accounts
            (request_id, teacher_id, email, password_hash, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash,
                expires_at    = EXCLUDED.expires_at,
                revoked_at    = NULL
        RETURNING id
        """,
        request_id,
        teacher_id,
        email,
        password_hash,
        NEVER_EXPIRES,
    )

    return {
        "name": name,
        "email": email,
        "password": password,
        "teacher_id": str(teacher_id),
        "account_id": str(account_id),
        "action": "created",
    }


# ── Students ───────────────────────────────────────────────────────────────────


async def _upsert_student(
    conn: asyncpg.Connection,
    school_id: str,
    student: dict,
) -> dict:
    """
    Upsert a demo student:
      students row         (auth_provider='demo', school_id=school_id)
      demo_requests row    (status='verified')
      demo_accounts row    (non-expiring)
      school_enrolments row (status='active')

    Returns a summary dict for the final report.
    """
    email = student["email"]
    name = student["name"]
    grade = student["grade"]
    password = student["password"]
    password_hash = _hash(password)

    # ── Check if demo_accounts row already exists ──────────────────────────────
    existing_account = await conn.fetchrow(
        "SELECT id, student_id FROM demo_accounts WHERE email = $1",
        email,
    )

    if existing_account:
        # Refresh password + expiry
        await conn.execute(
            """
            UPDATE demo_accounts
               SET password_hash = $1,
                   expires_at    = $2,
                   revoked_at    = NULL,
                   revoked_by    = NULL,
                   extended_at   = NOW()
             WHERE email = $3
            """,
            password_hash,
            NEVER_EXPIRES,
            email,
        )
        # Ensure student is linked to the correct school
        await conn.execute(
            """
            UPDATE students
               SET school_id = $1,
                   grade     = $2,
                   enrolled_at = COALESCE(enrolled_at, NOW())
             WHERE student_id = $3
            """,
            school_id,
            grade,
            existing_account["student_id"],
        )
        # Upsert enrolment
        await conn.execute(
            """
            INSERT INTO school_enrolments (school_id, student_email, student_id, status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (school_id, student_email) DO UPDATE
                SET student_id = EXCLUDED.student_id,
                    status     = 'active'
            """,
            school_id,
            email,
            existing_account["student_id"],
        )
        return {
            "name": name,
            "email": email,
            "password": password,
            "grade": grade,
            "student_id": str(existing_account["student_id"]),
            "account_id": str(existing_account["id"]),
            "action": "refreshed",
        }

    # ── Fresh create ───────────────────────────────────────────────────────────

    # demo_requests (seed placeholder)
    request_id = await conn.fetchval(
        """
        INSERT INTO demo_requests (email, ip_address, user_agent, status)
        VALUES ($1, 'seed-script', 'seed_demo_milfordwaterford.py', 'verified')
        RETURNING id
        """,
        email,
    )

    # students row
    demo_external_id = f"demo:{request_id}"
    student_id = await conn.fetchval(
        """
        INSERT INTO students
            (external_auth_id, auth_provider, name, email, grade, locale,
             account_status, school_id, enrolled_at)
        VALUES ($1, 'demo', $2, $3, $4, 'en', 'active', $5, NOW())
        ON CONFLICT (email) DO UPDATE
            SET school_id   = EXCLUDED.school_id,
                grade       = EXCLUDED.grade,
                name        = EXCLUDED.name,
                enrolled_at = COALESCE(students.enrolled_at, EXCLUDED.enrolled_at)
        RETURNING student_id
        """,
        demo_external_id,
        name,
        email,
        grade,
        school_id,
    )

    # demo_accounts
    account_id = await conn.fetchval(
        """
        INSERT INTO demo_accounts
            (request_id, student_id, email, password_hash, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash,
                expires_at    = EXCLUDED.expires_at,
                revoked_at    = NULL
        RETURNING id
        """,
        request_id,
        student_id,
        email,
        password_hash,
        NEVER_EXPIRES,
    )

    # school_enrolments
    await conn.execute(
        """
        INSERT INTO school_enrolments (school_id, student_email, student_id, status)
        VALUES ($1, $2, $3, 'active')
        ON CONFLICT (school_id, student_email) DO UPDATE
            SET student_id = EXCLUDED.student_id,
                status     = 'active'
        """,
        school_id,
        email,
        student_id,
    )

    return {
        "name": name,
        "email": email,
        "password": password,
        "grade": grade,
        "student_id": str(student_id),
        "account_id": str(account_id),
        "action": "created",
    }


# ── Main ───────────────────────────────────────────────────────────────────────


async def seed(dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] Would create/refresh the following accounts:\n")
        print(f"  School : {SCHOOL_NAME}")
        print()
        print("  Teachers:")
        for t in TEACHERS:
            print(f"    {t['name']:<20} {t['email']:<45} {t['password']}")
        print()
        print("  Students:")
        for s in STUDENTS:
            print(f"    {s['name']:<20} {s['email']:<45} {s['password']}  (Grade {s['grade']})")
        print()
        print("  expires_at: 2099-12-31 (non-expiring)")
        return

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            # Set RLS bypass so admin seed scripts can write across all tenant tables.
            await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
            async with conn.transaction():
                school_id = await _upsert_school(conn)
                print(f"\nSchool '{SCHOOL_NAME}'")
                print(_col("school_id", school_id))

                print("\nTeachers")
                print("─" * 70)
                teacher_results = []
                for t in TEACHERS:
                    result = await _upsert_teacher(conn, school_id, t)
                    teacher_results.append(result)
                    tag = f"[{result['action']}]"
                    print(f"  {result['name']:<22} {tag}")
                    print(_col("email", result["email"]))
                    print(_col("password", result["password"]))
                    print(_col("teacher_id", result["teacher_id"]))
                    print(_col("demo_account_id", result["account_id"]))
                    print(_col("login endpoint", "POST /api/v1/demo/teacher/auth/login"))
                    print()

                print("Students")
                print("─" * 70)
                student_results = []
                for s in STUDENTS:
                    result = await _upsert_student(conn, school_id, s)
                    student_results.append(result)
                    tag = f"[{result['action']}]"
                    print(f"  {result['name']:<22} Grade {result['grade']}  {tag}")
                    print(_col("email", result["email"]))
                    print(_col("password", result["password"]))
                    print(_col("student_id", result["student_id"]))
                    print(_col("demo_account_id", result["account_id"]))
                    print(_col("login endpoint", "POST /api/v1/demo/auth/login"))
                    print()

                print("─" * 70)
                print("All accounts expire: 2099-12-31 (non-expiring)")
                print("Done.")
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed or refresh MilfordWaterford Local School demo accounts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to the DB",
    )
    args = parser.parse_args()

    print("Seeding MilfordWaterford Local School demo accounts…")
    asyncio.run(seed(args.dry_run))


if __name__ == "__main__":
    main()
