"""
backend/src/admin/demo_seed.py

Shared async functions for seeding and wiping the demo school dataset.

Used by:
  - backend/scripts/seed_demo.py          (CLI: docker compose exec api python scripts/seed_demo.py)
  - POST /admin/demo/reset endpoint       (in-process, admin-only)

Demo school: "Riverside Academy"
  - 3 teachers  (school_admin + 2 subject teachers)
  - 30 students (grades 8–10)
  - 4 classrooms
  - 3 curricula (grades 8, 9, 10) loaded from data/ JSON files

All entities use deterministic fixed UUIDs (e0-prefix) so the seed is idempotent.
All demo users share one password: Demo2026!
first_login=False → users can log in immediately without a forced reset.

RLS: caller must stamp app.current_school_id='bypass' before running these
functions.  get_db() does this automatically for admin token requests.
"""

from __future__ import annotations

import asyncio
import functools
from datetime import UTC, datetime

import asyncpg
import bcrypt

from src.utils.logger import get_logger

log = get_logger("admin.demo_seed")

# ── Sentinel IDs (e0-prefix block reserved for demo school) ──────────────────

DEMO_SCHOOL_ID = "e0000000-0000-0000-0000-000000000001"
DEMO_SCHOOL_NAME = "Riverside Academy"
DEMO_CONTACT_EMAIL = "admin@riverside.demo"
DEMO_PASSWORD = "Demo2026!"

_TEACHER_ADMIN_ID = "e0000000-0000-0000-0000-000000000010"
_TEACHER_MATH_ID = "e0000000-0000-0000-0000-000000000011"
_TEACHER_SCI_ID = "e0000000-0000-0000-0000-000000000012"

_TEACHERS = [
    {
        "teacher_id": _TEACHER_ADMIN_ID,
        "name": "Sarah Chen",
        "email": "sarah.chen@riverside.demo",
        "role": "school_admin",
    },
    {
        "teacher_id": _TEACHER_MATH_ID,
        "name": "James Okonkwo",
        "email": "james.okonkwo@riverside.demo",
        "role": "teacher",
    },
    {
        "teacher_id": _TEACHER_SCI_ID,
        "name": "Maria Santos",
        "email": "maria.santos@riverside.demo",
        "role": "teacher",
    },
]

_STUDENTS: list[dict] = [
    # ── Grade 8 (n=1–12) ──────────────────────────────────────────────────────
    {"n": 1, "name": "Aiden Park", "grade": 8},
    {"n": 2, "name": "Sophia Chen", "grade": 8},
    {"n": 3, "name": "Marcus Johnson", "grade": 8},
    {"n": 4, "name": "Isabella Garcia", "grade": 8},
    {"n": 5, "name": "Ethan Patel", "grade": 8},
    {"n": 6, "name": "Olivia Kim", "grade": 8},
    {"n": 7, "name": "Noah Williams", "grade": 8},
    {"n": 8, "name": "Emma Rodriguez", "grade": 8},
    {"n": 9, "name": "Liam Thompson", "grade": 8},
    {"n": 10, "name": "Ava Martinez", "grade": 8},
    {"n": 11, "name": "Mason Lee", "grade": 8},
    {"n": 12, "name": "Charlotte Brown", "grade": 8},
    # ── Grade 9 (n=13–22) ────────────────────────────────────────────────────
    {"n": 13, "name": "Jackson Davis", "grade": 9},
    {"n": 14, "name": "Mia Wilson", "grade": 9},
    {"n": 15, "name": "Lucas Taylor", "grade": 9},
    {"n": 16, "name": "Amelia Anderson", "grade": 9},
    {"n": 17, "name": "Benjamin Moore", "grade": 9},
    {"n": 18, "name": "Harper Jackson", "grade": 9},
    {"n": 19, "name": "Alexander White", "grade": 9},
    {"n": 20, "name": "Evelyn Harris", "grade": 9},
    {"n": 21, "name": "Daniel Lewis", "grade": 9},
    {"n": 22, "name": "Abigail Clark", "grade": 9},
    # ── Grade 10 (n=23–30) ───────────────────────────────────────────────────
    {"n": 23, "name": "Henry Walker", "grade": 10},
    {"n": 24, "name": "Emily Hall", "grade": 10},
    {"n": 25, "name": "James Allen", "grade": 10},
    {"n": 26, "name": "Elizabeth Young", "grade": 10},
    {"n": 27, "name": "William King", "grade": 10},
    {"n": 28, "name": "Sofia Wright", "grade": 10},
    {"n": 29, "name": "Sebastian Scott", "grade": 10},
    {"n": 30, "name": "Chloe Green", "grade": 10},
]

# Demo classrooms point at the REAL platform curricula — the same ones the
# pipeline generates into. They used to point at a private `demo-2026-g*`
# namespace that this seeder created rows for but never generated content for,
# so the Subjects tree rendered (it reads curriculum_units) while every
# lesson/quiz 404'd with "This isn't available yet".
#
# Note the ids are not uniform: the STEM curricula for grades 5–9 carry a
# `-stem` suffix, grades 10–12 do not. Take these from the content store, do not
# infer them.
_CLASSROOMS = [
    {
        "classroom_id": "e0000000-0000-0000-0002-000000000001",
        "name": "Grade 8 Mathematics & Technology",
        "grade": 8,
        "teacher_id": _TEACHER_MATH_ID,
        "curriculum_id": "default-2026-g8",
        "student_ns": range(1, 7),
    },
    {
        "classroom_id": "e0000000-0000-0000-0002-000000000002",
        "name": "Grade 8 Science & Engineering",
        "grade": 8,
        "teacher_id": _TEACHER_SCI_ID,
        "curriculum_id": "default-2026-g8",
        "student_ns": range(7, 13),
    },
    {
        "classroom_id": "e0000000-0000-0000-0002-000000000003",
        "name": "Grade 9 STEM",
        "grade": 9,
        "teacher_id": _TEACHER_MATH_ID,
        "curriculum_id": "default-2026-g9-stem",
        "student_ns": range(13, 23),
    },
    {
        "classroom_id": "e0000000-0000-0000-0002-000000000004",
        "name": "Grade 10 Advanced STEM",
        "grade": 10,
        "teacher_id": _TEACHER_SCI_ID,
        "curriculum_id": "default-2026-g10",
        "student_ns": range(23, 31),
    },
]

# Legacy ids this seeder used to create. Retained ONLY so teardown can clean up
# rows left behind by older runs. Never add a `default-*` id here — teardown
# DELETEs these, and the default-* curricula are real platform content.
_LEGACY_DEMO_CURRICULA = ["demo-2026-g8", "demo-2026-g9", "demo-2026-g10"]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _student_id(n: int) -> str:
    return f"e0000000-0000-0000-0001-{n:012d}"


def _student_email(name: str) -> str:
    parts = name.lower().split()
    return f"{parts[0]}.{parts[-1]}@riverside.demo"


async def _hash_once(password: str) -> str:
    """Compute a bcrypt hash on the thread pool (rounds=10 for demo speed)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        functools.partial(
            lambda pw: bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode(),
            password,
        ),
    )


# ── Core operations ───────────────────────────────────────────────────────────


async def wipe_demo(conn: asyncpg.Connection) -> None:
    """
    Delete all demo school data in FK-safe order.

    students.school_id is ON DELETE SET NULL (not CASCADE), so students must
    be deleted explicitly before the school row is removed.
    """
    await conn.execute("DELETE FROM students WHERE school_id = $1", DEMO_SCHOOL_ID)
    await conn.execute("DELETE FROM teachers WHERE school_id = $1", DEMO_SCHOOL_ID)
    # Only the legacy demo-owned curricula. The demo now points at real
    # `default-*` platform curricula — deleting those would destroy the
    # platform's content registry for every school.
    await conn.execute(
        "DELETE FROM curricula WHERE curriculum_id = ANY($1::text[])",
        _LEGACY_DEMO_CURRICULA,
    )
    # CASCADE removes: classrooms → classroom_students, classroom_packages
    # CASCADE removes: school_enrolments
    await conn.execute("DELETE FROM schools WHERE school_id = $1", DEMO_SCHOOL_ID)


async def seed_demo(conn: asyncpg.Connection) -> dict:
    """
    Insert all demo school data.  Idempotent — skips rows that already exist.

    Returns a summary dict with counts of inserted rows.
    """
    demo_hash = await _hash_once(DEMO_PASSWORD)
    school_uuid = DEMO_SCHOOL_ID
    counts: dict[str, int] = {
        "schools": 0,
        "teachers": 0,
        "students": 0,
        "curricula": 0,
        "units": 0,
        "classrooms": 0,
    }

    # ── School ────────────────────────────────────────────────────────────────
    result = await conn.execute(
        """
        INSERT INTO schools (school_id, name, contact_email, country, status)
        VALUES ($1, $2, $3, 'US', 'active')
        ON CONFLICT (school_id) DO NOTHING
        """,
        school_uuid,
        DEMO_SCHOOL_NAME,
        DEMO_CONTACT_EMAIL,
    )
    counts["schools"] = 0 if result == "INSERT 0 0" else 1

    # ── Teachers ──────────────────────────────────────────────────────────────
    for t in _TEACHERS:
        r = await conn.execute(
            """
            INSERT INTO teachers
                (teacher_id, school_id, external_auth_id, auth_provider,
                 name, email, password_hash, role, account_status, first_login)
            VALUES ($1, $2, $3, 'local', $4, $5, $6, $7, 'active', FALSE)
            ON CONFLICT (teacher_id) DO NOTHING
            """,
            t["teacher_id"],
            school_uuid,
            f"local:{t['teacher_id']}",
            t["name"],
            t["email"],
            demo_hash,
            t["role"],
        )
        if r != "INSERT 0 0":
            counts["teachers"] += 1

    # ── Students ──────────────────────────────────────────────────────────────
    for s in _STUDENTS:
        sid = _student_id(s["n"])
        email = _student_email(s["name"])
        r = await conn.execute(
            """
            INSERT INTO students
                (student_id, school_id, external_auth_id, auth_provider,
                 name, email, password_hash, grade, account_status, first_login)
            VALUES ($1, $2, $3, 'local', $4, $5, $6, $7, 'active', FALSE)
            ON CONFLICT (student_id) DO NOTHING
            """,
            sid,
            school_uuid,
            f"local:{sid}",
            s["name"],
            email,
            demo_hash,
            s["grade"],
        )
        if r != "INSERT 0 0":
            counts["students"] += 1

        # Enrolment record (active, grade set)
        await conn.execute(
            """
            INSERT INTO school_enrolments
                (school_id, student_email, student_id, status, grade)
            VALUES ($1, $2, $3, 'active', $4)
            ON CONFLICT (school_id, student_email) DO NOTHING
            """,
            school_uuid,
            email,
            sid,
            s["grade"],
        )

    # ── Curricula ─────────────────────────────────────────────────────────────
    # The demo no longer creates its own curricula. It consumes the real platform
    # ones, which the pipeline generates and `scripts/backfill_content_registry.py`
    # registers. Verify they are present rather than silently seeding a classroom
    # that points at nothing — an unregistered curriculum renders a Subjects tree
    # whose every lesson and quiz 404s.
    for curriculum_id in sorted({cl["curriculum_id"] for cl in _CLASSROOMS}):
        published = await conn.fetchval(
            """
            SELECT COUNT(*) FROM content_subject_versions
            WHERE curriculum_id = $1 AND status = 'published'
            """,
            curriculum_id,
        )
        if not published:
            log.warning(
                "demo_seed_curriculum_has_no_published_content",
                extra={"curriculum_id": curriculum_id},
            )

    # ── Classrooms ────────────────────────────────────────────────────────────
    for cl in _CLASSROOMS:
        r = await conn.execute(
            """
            INSERT INTO classrooms
                (classroom_id, school_id, teacher_id, name, grade, status)
            VALUES ($1, $2, $3, $4, $5, 'active')
            ON CONFLICT (classroom_id) DO NOTHING
            """,
            cl["classroom_id"],
            school_uuid,
            cl["teacher_id"],
            cl["name"],
            cl["grade"],
        )
        if r != "INSERT 0 0":
            counts["classrooms"] += 1

        # Package assignment
        # Evict any package this seeder attached previously that is no longer the
        # intended one. Without this, re-seeding over an older demo leaves the
        # classroom with two packages, and the curriculum resolver takes only the
        # first (content/service.py) — so it can still land on the dead
        # `demo-2026-*` curriculum and 404 every lesson.
        await conn.execute(
            """
            DELETE FROM classroom_packages
            WHERE classroom_id = $1 AND curriculum_id <> $2
            """,
            cl["classroom_id"],
            cl["curriculum_id"],
        )
        await conn.execute(
            """
            INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order)
            VALUES ($1, $2, 0)
            ON CONFLICT (classroom_id, curriculum_id) DO NOTHING
            """,
            cl["classroom_id"],
            cl["curriculum_id"],
        )

        # Student enrolments
        for n in cl["student_ns"]:
            await conn.execute(
                """
                INSERT INTO classroom_students (classroom_id, student_id)
                VALUES ($1, $2)
                ON CONFLICT (classroom_id, student_id) DO NOTHING
                """,
                cl["classroom_id"],
                _student_id(n),
            )

    return counts


async def reset_demo(conn: asyncpg.Connection) -> dict:
    """
    Wipe the demo school and re-seed it.

    Returns a summary dict suitable for the API response:
      { school, teachers, students, curricula, units, classrooms, reset_at }
    """
    await wipe_demo(conn)
    counts = await seed_demo(conn)
    return {
        "school": DEMO_SCHOOL_NAME,
        "teachers_seeded": counts["teachers"],
        "students_seeded": counts["students"],
        "curricula_seeded": counts["curricula"],
        "units_seeded": counts["units"],
        "classrooms_seeded": counts["classrooms"],
        "reset_at": datetime.now(tz=UTC).isoformat(),
    }
