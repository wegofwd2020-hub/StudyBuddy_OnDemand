#!/usr/bin/env python3
"""
backend/scripts/seed_demo_milfordwaterford.py

Creates (or refreshes) a full demo school environment for MilfordWaterford
Local School — used for manual QA, product demos, and investor showcases.

Accounts created
────────────────
  School   : MilfordWaterford Local School

  Teachers (login via POST /demo/teacher/auth/login):
    sam.houston@milfordwaterford.edu     / MWTeacher-Sam-2026!
    linda.ronstad@milfordwaterford.edu   / MWTeacher-Linda-2026!
    warren.buffett@milfordwaterford.edu  / MWTeacher-Warren-2026!  (Commerce)
    indra.nooyi@milfordwaterford.edu     / MWTeacher-Indra-2026!   (Commerce)

  Students (login via POST /demo/auth/login):
    samjr@milfordwaterford.edu          / MWStudent-SamJr-2026!    Grade 8
    jose.herbert@milfordwaterford.edu   / MWStudent-Jose-2026!     Grade 8
    priya.sharma@milfordwaterford.edu   / MWStudent-Priya-2026!    Grade 10
    carlos.mendez@milfordwaterford.edu  / MWStudent-Carlos-2026!   Grade 10
    emma.thompson@milfordwaterford.edu  / MWStudent-Emma-2026!     Grade 11 (STEM)
    david.chen@milfordwaterford.edu     / MWStudent-David-2026!    Grade 11 (STEM)
    anya.iyer@milfordwaterford.edu      / MWStudent-Anya-2026!     Grade 11 (Commerce)
    raj.kapoor@milfordwaterford.edu     / MWStudent-Raj-2026!      Grade 11 (Commerce)
    mei.chen@milfordwaterford.edu       / MWStudent-Mei-2026!      Grade 11 (Commerce)
    fatima.alhassan@milfordwaterford.edu / MWStudent-Fatima-2026!  Grade 11 (Science)
    liam.obrien@milfordwaterford.edu    / MWStudent-Liam-2026!     Grade 11 (Science)
    isabella.costa@milfordwaterford.edu / MWStudent-Isabella-2026! Grade 12 (Commerce)
    james.adeyemi@milfordwaterford.edu  / MWStudent-James-2026!    Grade 12 (Commerce)
    samsr@milfordwaterford.edu          / MWStudent-SamSr-2026!    Grade 12 (Science)
    linda.herbert@milfordwaterford.edu  / MWStudent-Linda-2026!    Grade 12 (Science)

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
        "role": "school_admin",
    },
    {
        "name": "Linda Ronstad",
        "email": "linda.ronstad@milfordwaterford.edu",
        "password": "MWTeacher-Linda-2026!",
        "role": "teacher",
    },
    # Commerce-stream teachers (Grade 11). Added to support testing of
    # Balance Sheet / P&L / Accountancy content flow end-to-end.
    {
        "name": "Warren Buffett",
        "email": "warren.buffett@milfordwaterford.edu",
        "password": "MWTeacher-Warren-2026!",
        "role": "teacher",
    },
    {
        "name": "Indra Nooyi",
        "email": "indra.nooyi@milfordwaterford.edu",
        "password": "MWTeacher-Indra-2026!",
        "role": "teacher",
    },
]

# Classrooms: group students by grade, assign lead teachers.
# curriculum_ids reference the default platform curricula that must already
# exist (seeded by seed_default.py / build_grade.py).
CLASSROOMS: list[dict] = [
    {
        "name": "Grade 8 — General STEM",
        "grade": 8,
        "teacher_email": "sam.houston@milfordwaterford.edu",
        "curriculum_id": "default-2026-g8",
        "curriculum_name": "Grade 8 STEM 2026",
        "student_emails": [
            "samjr@milfordwaterford.edu",
            "jose.herbert@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 10 — STEM",
        "grade": 10,
        "teacher_email": "indra.nooyi@milfordwaterford.edu",
        "curriculum_id": "default-2026-g10",
        "curriculum_name": "Grade 10 STEM 2026",
        "student_emails": [
            "priya.sharma@milfordwaterford.edu",
            "carlos.mendez@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 11 — STEM",
        "grade": 11,
        "teacher_email": "sam.houston@milfordwaterford.edu",
        "curriculum_id": "default-2026-g11",
        "curriculum_name": "Grade 11 STEM 2026",
        "student_emails": [
            "emma.thompson@milfordwaterford.edu",
            "david.chen@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 11 — Commerce",
        "grade": 11,
        "teacher_email": "warren.buffett@milfordwaterford.edu",
        "curriculum_id": "default-2026-g11-commerce",
        "curriculum_name": "Grade 11 Commerce 2026",
        "student_emails": [
            "anya.iyer@milfordwaterford.edu",
            "raj.kapoor@milfordwaterford.edu",
            "mei.chen@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 11 — Science",
        "grade": 11,
        "teacher_email": "linda.ronstad@milfordwaterford.edu",
        "curriculum_id": "default-2026-g11-science",
        "curriculum_name": "Grade 11 Science 2026",
        "student_emails": [
            "fatima.alhassan@milfordwaterford.edu",
            "liam.obrien@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 12 — Commerce",
        "grade": 12,
        "teacher_email": "warren.buffett@milfordwaterford.edu",
        "curriculum_id": "default-2026-g12-commerce",
        "curriculum_name": "Grade 12 Commerce 2026",
        "student_emails": [
            "isabella.costa@milfordwaterford.edu",
            "james.adeyemi@milfordwaterford.edu",
        ],
    },
    {
        "name": "Grade 12 — Science",
        "grade": 12,
        "teacher_email": "linda.ronstad@milfordwaterford.edu",
        "curriculum_id": "default-2026-g12-science",
        "curriculum_name": "Grade 12 Science 2026",
        "student_emails": [
            "samsr@milfordwaterford.edu",
            "linda.herbert@milfordwaterford.edu",
        ],
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
    # Grade 10 STEM
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@milfordwaterford.edu",
        "password": "MWStudent-Priya-2026!",
        "grade": 10,
    },
    {
        "name": "Carlos Mendez",
        "email": "carlos.mendez@milfordwaterford.edu",
        "password": "MWStudent-Carlos-2026!",
        "grade": 10,
    },
    # Grade 11 STEM
    {
        "name": "Emma Thompson",
        "email": "emma.thompson@milfordwaterford.edu",
        "password": "MWStudent-Emma-2026!",
        "grade": 11,
    },
    {
        "name": "David Chen",
        "email": "david.chen@milfordwaterford.edu",
        "password": "MWStudent-David-2026!",
        "grade": 11,
    },
    # Grade 11 Commerce students — pair with Warren Buffett teacher
    {
        "name": "Anya Iyer",
        "email": "anya.iyer@milfordwaterford.edu",
        "password": "MWStudent-Anya-2026!",
        "grade": 11,
    },
    {
        "name": "Raj Kapoor",
        "email": "raj.kapoor@milfordwaterford.edu",
        "password": "MWStudent-Raj-2026!",
        "grade": 11,
    },
    {
        "name": "Mei Chen",
        "email": "mei.chen@milfordwaterford.edu",
        "password": "MWStudent-Mei-2026!",
        "grade": 11,
    },
    # Grade 11 Science
    {
        "name": "Fatima Al-Hassan",
        "email": "fatima.alhassan@milfordwaterford.edu",
        "password": "MWStudent-Fatima-2026!",
        "grade": 11,
    },
    {
        "name": "Liam O'Brien",
        "email": "liam.obrien@milfordwaterford.edu",
        "password": "MWStudent-Liam-2026!",
        "grade": 11,
    },
    # Grade 12 Commerce
    {
        "name": "Isabella Costa",
        "email": "isabella.costa@milfordwaterford.edu",
        "password": "MWStudent-Isabella-2026!",
        "grade": 12,
    },
    {
        "name": "James Adeyemi",
        "email": "james.adeyemi@milfordwaterford.edu",
        "password": "MWStudent-James-2026!",
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


async def _ensure_subscription(conn: asyncpg.Connection, school_id: str) -> None:
    """Give the demo school an active subscription.

    Without one the school falls to the free tier, whose cap is TWO lessons
    (`_FREE_TIER_LESSON_LIMIT` in content/router.py) — so a seeded student opens
    two lessons and every one after that returns 402. The accounts look fine
    right up until someone actually uses them, which is exactly what happened on
    2026-08-31: the seeded school had no subscription and the gap was missed
    because a differently-named school on the same demo did have one.

    Idempotent, and it does not touch an existing row: a school whose
    subscription was deliberately expired for paywall testing stays expired.
    """
    await conn.execute(
        """
        INSERT INTO school_subscriptions
            (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
             max_students, max_teachers, current_period_end)
        SELECT $1, 'professional', 'active',
               'cus_demo_milford_local', 'sub_demo_milford_local', 500, 50,
               NOW() + INTERVAL '1 year'
        WHERE NOT EXISTS (
            SELECT 1 FROM school_subscriptions WHERE school_id = $1
        )
        """,
        school_id,
    )


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
                name      = EXCLUDED.name,
                role      = EXCLUDED.role
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


# ── Classrooms ────────────────────────────────────────────────────────────────


async def _upsert_classrooms(
    conn: asyncpg.Connection,
    school_id: str,
) -> list[dict]:
    """
    Create (or skip existing) classrooms, package assignments, and student
    enrolments for MilfordWaterford.

    Teacher and student rows must already exist before calling this.
    curriculum_id rows are inserted as stubs if they don't exist yet so the
    classroom package link doesn't fail on a fresh DB.
    """
    results = []
    for cl in CLASSROOMS:
        # Resolve teacher_id from email
        teacher_id = await conn.fetchval(
            "SELECT teacher_id FROM teachers WHERE email = $1", cl["teacher_email"]
        )
        if not teacher_id:
            print(f"  [warn] teacher not found for classroom '{cl['name']}' — skipping")
            continue

        # Ensure curriculum row exists so classroom_packages FK succeeds.
        # The pipeline (build_grade.py) will have already inserted the real row;
        # this is a no-op in that case.  On a fresh DB it inserts a stub so the
        # classroom can be linked before content is generated.
        await conn.execute(
            """
            INSERT INTO curricula (curriculum_id, grade, year, name, is_default)
            VALUES ($1, $2, 2026, $3, FALSE)
            ON CONFLICT (curriculum_id) DO NOTHING
            """,
            cl["curriculum_id"],
            cl["grade"],
            cl["curriculum_name"],
        )

        # Classroom row
        classroom_id = await conn.fetchval(
            """
            INSERT INTO classrooms (school_id, teacher_id, name, grade, status)
            VALUES ($1, $2, $3, $4, 'active')
            ON CONFLICT DO NOTHING
            RETURNING classroom_id
            """,
            school_id,
            teacher_id,
            cl["name"],
            cl["grade"],
        )
        if classroom_id is None:
            # Already exists — look it up
            classroom_id = await conn.fetchval(
                "SELECT classroom_id FROM classrooms WHERE school_id = $1 AND name = $2",
                school_id,
                cl["name"],
            )
            action = "existing"
        else:
            action = "created"

        # Package assignment — remove any stale packages then (re)insert the correct one
        await conn.execute(
            "DELETE FROM classroom_packages WHERE classroom_id = $1",
            classroom_id,
        )
        await conn.execute(
            """
            INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order)
            VALUES ($1, $2, 0)
            ON CONFLICT (classroom_id, curriculum_id) DO UPDATE SET sort_order = 0
            """,
            classroom_id,
            cl["curriculum_id"],
        )

        # Student enrolments
        enrolled = 0
        for email in cl["student_emails"]:
            student_id = await conn.fetchval(
                "SELECT student_id FROM students WHERE email = $1", email
            )
            if not student_id:
                print(f"    [warn] student {email} not found — skipping")
                continue
            await conn.execute(
                """
                INSERT INTO classroom_students (classroom_id, student_id)
                VALUES ($1, $2)
                ON CONFLICT (classroom_id, student_id) DO NOTHING
                """,
                classroom_id,
                student_id,
            )
            enrolled += 1

        results.append(
            {
                "name": cl["name"],
                "classroom_id": str(classroom_id),
                "teacher": cl["teacher_email"],
                "students": enrolled,
                "action": action,
            }
        )
    return results


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
        print("  Classrooms:")
        for cl in CLASSROOMS:
            print(f"    Grade {cl['grade']} — {cl['name']}  ({len(cl['student_emails'])} students)")
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
                await _ensure_subscription(conn, school_id)
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

                print("Classrooms")
                print("─" * 70)
                classroom_results = await _upsert_classrooms(conn, school_id)
                for cl in classroom_results:
                    tag = f"[{cl['action']}]"
                    print(f"  {cl['name']:<30} {tag}")
                    print(_col("classroom_id", cl["classroom_id"]))
                    print(_col("teacher", cl["teacher"]))
                    print(_col("students enrolled", cl["students"]))
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
