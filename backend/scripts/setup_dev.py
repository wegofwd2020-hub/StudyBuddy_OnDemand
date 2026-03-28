#!/usr/bin/env python3
"""
backend/scripts/setup_dev.py

Master developer environment setup script.

Creates all dev accounts, seeds Grade 8 curriculum content, and inserts
realistic test data (progress sessions, lesson views) so every portal
page renders with meaningful data immediately after `docker compose up`.

Safe to run multiple times — all operations are idempotent.

Usage:
  docker compose exec api python scripts/setup_dev.py
  docker compose exec api python scripts/setup_dev.py --reset   # wipe dev data first

Accounts created:
  Role         Email                            Password / Method
  ─────────────────────────────────────────────────────────────────
  super_admin  dev.admin@studybuddy.dev         DevAdmin1234!  (admin portal)
  school_admin dev.schooladmin@studybuddy.dev   /dev-login     (school portal)
  teacher      dev.teacher@studybuddy.dev       /dev-login     (school portal)
  student      dev.student@studybuddy.dev       /dev-login     (student portal)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg

# ── Configuration ─────────────────────────────────────────────────────────────

# Always connect directly to Postgres — never through PgBouncer.
# PgBouncer transaction-pooling silently drops asyncpg prepared statements.
_raw_url = os.environ.get("DATABASE_URL", "")
if not _raw_url:
    _pg_pass = os.environ.get("POSTGRES_PASSWORD", "studybuddy_dev")
    _raw_url = f"postgresql://studybuddy:{_pg_pass}@db:5432/studybuddy"
DATABASE_URL = _raw_url.replace("@pgbouncer:", "@db:")

CONTENT_STORE_PATH = os.environ.get("CONTENT_STORE_PATH", "/data/content")
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ── Fixed Dev Identity Constants ───────────────────────────────────────────────
# UUIDs are stable so URLs/bookmarks remain valid across resets.

DEV_SCHOOL_ID          = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_STUDENT_SUB        = "dev|student-001"
DEV_TEACHER_SUB        = "dev|teacher-001"
DEV_SCHOOL_ADMIN_SUB   = "dev|school-admin-001"
CURRICULUM_ID          = "default-2026-g8"

DEV_ADMIN_EMAIL        = "dev.admin@studybuddy.dev"
DEV_ADMIN_PASSWORD     = "DevAdmin1234!"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(UTC)

def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)

def _hash_password(password: str) -> str:
    """bcrypt hash — same method as the auth service."""
    import bcrypt as _bcrypt
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()

def _banner(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print('─' * 60)

def _ok(label: str, value: str = "") -> None:
    suffix = f"  {value}" if value else ""
    print(f"  ✓  {label}{suffix}")

def _skip(label: str) -> None:
    print(f"  –  {label} (already exists)")

# ── Step 1: Dev School ────────────────────────────────────────────────────────

async def setup_school(conn: asyncpg.Connection) -> None:
    _banner("School")
    exists = await conn.fetchval(
        "SELECT 1 FROM schools WHERE school_id = $1", DEV_SCHOOL_ID
    )
    if exists:
        _skip("Dev School")
        return
    await conn.execute(
        """
        INSERT INTO schools (school_id, name, contact_email, country, enrolment_code, status)
        VALUES ($1, 'Dev School', 'dev@studybuddy.dev', 'CA', 'DEVSCHOOL01', 'active')
        ON CONFLICT (school_id) DO NOTHING
        """,
        DEV_SCHOOL_ID,
    )
    _ok("Dev School created", f"id={DEV_SCHOOL_ID}  code=DEVSCHOOL01")

# ── Step 2: Super Admin ───────────────────────────────────────────────────────

async def setup_super_admin(conn: asyncpg.Connection) -> None:
    _banner("Super Admin")
    exists = await conn.fetchval(
        "SELECT 1 FROM admin_users WHERE email = $1", DEV_ADMIN_EMAIL
    )
    if exists:
        _skip(DEV_ADMIN_EMAIL)
        return
    pw_hash = await asyncio.get_event_loop().run_in_executor(
        None, _hash_password, DEV_ADMIN_PASSWORD
    )
    await conn.execute(
        """
        INSERT INTO admin_users (email, password_hash, role, account_status)
        VALUES ($1, $2, 'super_admin', 'active')
        ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
        """,
        DEV_ADMIN_EMAIL,
        pw_hash,
    )
    _ok(DEV_ADMIN_EMAIL, f"role=super_admin  password={DEV_ADMIN_PASSWORD}")

# ── Step 3: School Admin Teacher ──────────────────────────────────────────────

async def setup_school_admin(conn: asyncpg.Connection) -> None:
    _banner("School Admin Teacher")
    exists = await conn.fetchval(
        "SELECT 1 FROM teachers WHERE external_auth_id = $1", DEV_SCHOOL_ADMIN_SUB
    )
    if exists:
        _skip("dev.schooladmin@studybuddy.dev")
        return
    await conn.execute(
        """
        INSERT INTO teachers
            (school_id, external_auth_id, auth_provider, name, email, role, account_status)
        VALUES ($1, $2, 'dev', 'Dev School Admin', 'dev.schooladmin@studybuddy.dev', 'school_admin', 'active')
        ON CONFLICT (external_auth_id) DO NOTHING
        """,
        DEV_SCHOOL_ID,
        DEV_SCHOOL_ADMIN_SUB,
    )
    _ok("dev.schooladmin@studybuddy.dev", "role=school_admin  login=/dev-login")

# ── Step 4: Teacher ───────────────────────────────────────────────────────────

async def setup_teacher(conn: asyncpg.Connection) -> None:
    _banner("Teacher")
    exists = await conn.fetchval(
        "SELECT 1 FROM teachers WHERE external_auth_id = $1", DEV_TEACHER_SUB
    )
    if exists:
        _skip("dev.teacher@studybuddy.dev")
        return
    await conn.execute(
        """
        INSERT INTO teachers
            (school_id, external_auth_id, auth_provider, name, email, role, account_status)
        VALUES ($1, $2, 'dev', 'Dev Teacher', 'dev.teacher@studybuddy.dev', 'teacher', 'active')
        ON CONFLICT (external_auth_id) DO NOTHING
        """,
        DEV_SCHOOL_ID,
        DEV_TEACHER_SUB,
    )
    _ok("dev.teacher@studybuddy.dev", "role=teacher  login=/dev-login")

# ── Step 5: Student ───────────────────────────────────────────────────────────

async def setup_student(conn: asyncpg.Connection) -> uuid.UUID:
    _banner("Student")
    row = await conn.fetchrow(
        "SELECT student_id FROM students WHERE external_auth_id = $1",
        DEV_STUDENT_SUB,
    )
    if row is None:
        row = await conn.fetchrow(
            """
            INSERT INTO students
                (external_auth_id, auth_provider, name, email, grade, locale,
                 account_status, school_id, enrolled_at)
            VALUES ($1, 'dev', 'Dev Student', 'dev.student@studybuddy.dev',
                    8, 'en', 'active', $2, NOW())
            RETURNING student_id
            """,
            DEV_STUDENT_SUB,
            DEV_SCHOOL_ID,
        )
        _ok("dev.student@studybuddy.dev", "grade=8  school=Dev School  login=/dev-login")
    else:
        # Ensure enrolled in Dev School
        await conn.execute(
            "UPDATE students SET school_id = $1, enrolled_at = COALESCE(enrolled_at, NOW()) WHERE student_id = $2",
            DEV_SCHOOL_ID,
            row["student_id"],
        )
        _skip("dev.student@studybuddy.dev")

    student_id: uuid.UUID = row["student_id"]

    # Premium entitlement — bypasses 2-lesson free-tier paywall
    await conn.execute(
        """
        INSERT INTO student_entitlements (student_id, plan, lessons_accessed, valid_until)
        VALUES ($1, 'premium', 0, NOW() + INTERVAL '1 year')
        ON CONFLICT (student_id) DO UPDATE
            SET plan = 'premium', valid_until = NOW() + INTERVAL '1 year'
        """,
        student_id,
    )
    _ok("Premium entitlement active", "expires in 1 year")
    return student_id

# ── Step 6: Curriculum + Content ─────────────────────────────────────────────

async def setup_curriculum(conn: asyncpg.Connection) -> list[dict]:
    """Seed Grade 8 curriculum rows and content files. Returns list of units."""
    _banner("Curriculum & Content")

    grade_file = DATA_DIR / "grade8_stem.json"
    if not grade_file.exists():
        print(f"  !  {grade_file} not found — skipping curriculum seed")
        return []

    with open(grade_file) as f:
        grade_data = json.load(f)

    # Upsert curricula row
    await conn.execute(
        """
        INSERT INTO curricula (curriculum_id, grade, year, is_default, name, status)
        VALUES ($1, 8, 2026, TRUE, 'Grade 8 STEM 2026', 'active')
        ON CONFLICT (curriculum_id) DO NOTHING
        """,
        CURRICULUM_ID,
    )

    units: list[dict] = []
    subjects_seen: set[str] = set()

    for sort_idx, subject_data in enumerate(grade_data.get("subjects", []), start=1):
        # JSON uses subject_id (e.g. "G8-MATH") as the subject code
        subject_name = subject_data["subject_id"]
        for seq_idx, unit in enumerate(subject_data.get("units", []), start=1):
            unit_id = unit["unit_id"]
            unit_title = unit.get("title", unit_id)
            has_lab = unit.get("has_lab", False)
            units.append({"unit_id": unit_id, "subject": subject_name, "title": unit_title})

            await conn.execute(
                """
                INSERT INTO curriculum_units
                    (curriculum_id, unit_id, subject, title, unit_name, has_lab,
                     sort_order, sequence, content_status)
                VALUES ($1, $2, $3, $4, $4, $5, $6, $7, 'built')
                ON CONFLICT (unit_id, curriculum_id) DO NOTHING
                """,
                CURRICULUM_ID,
                unit_id,
                subject_name,
                unit_title,
                has_lab,
                sort_idx,
                seq_idx,
            )

            # Content files
            _write_content_files(unit_id, subject_name, unit_title)

        # Subject version (published)
        if subject_name not in subjects_seen:
            subjects_seen.add(subject_name)
            await conn.execute(
                """
                INSERT INTO content_subject_versions
                    (curriculum_id, subject, version_number, status, published_at)
                VALUES ($1, $2, 1, 'published', NOW())
                ON CONFLICT (curriculum_id, subject, version_number)
                DO UPDATE SET status = 'published', published_at = NOW()
                """,
                CURRICULUM_ID,
                subject_name,
            )

    _ok(f"Curriculum seeded", f"{len(units)} units  {len(subjects_seen)} subjects")
    return units

def _write_content_files(unit_id: str, subject: str, title: str) -> None:
    unit_dir = Path(CONTENT_STORE_PATH) / "curricula" / CURRICULUM_ID / unit_id
    unit_dir.mkdir(parents=True, exist_ok=True)

    # Lesson
    lesson_path = unit_dir / "lesson_en.json"
    if not lesson_path.exists():
        lesson_path.write_text(json.dumps({
            "unit_id": unit_id,
            "title": title,
            "grade": 8,
            "subject": subject,
            "lang": "en",
            "sections": [
                {"heading": "Introduction", "body": f"Welcome to {title}. In this lesson you will explore the core concepts of {subject}."},
                {"heading": "Core Concepts", "body": f"The key ideas in {title} build on what you already know about {subject}."},
                {"heading": "Worked Example", "body": "Let's walk through a step-by-step example to make this concrete."},
                {"heading": "Practice", "body": "Apply what you've learned by working through the practice problems below."},
            ],
            "key_points": [f"Understand the basics of {title}", f"Apply {subject} principles", "Practice with examples"],
            "has_audio": False,
            "generated_at": _now().isoformat(),
            "model": "dev-placeholder",
            "content_version": 1,
        }, indent=2))

    # Quiz sets 1-3
    for set_num in range(1, 4):
        quiz_path = unit_dir / f"quiz_set_{set_num}_en.json"
        if not quiz_path.exists():
            quiz_path.write_text(json.dumps({
                "unit_id": unit_id,
                "set_number": set_num,
                "language": "en",
                "questions": [
                    {
                        "question_id": f"{unit_id}-S{set_num}-Q{i}",
                        "question_text": f"[Set {set_num}] Sample question {i} about {title}?",
                        "question_type": "multiple_choice",
                        "options": [
                            {"option_id": "A", "text": "Option A (correct)"},
                            {"option_id": "B", "text": "Option B"},
                            {"option_id": "C", "text": "Option C"},
                            {"option_id": "D", "text": "Option D"},
                        ],
                        "correct_option": "A",
                        "explanation": "Option A is correct because it best represents the concept.",
                        "difficulty": "medium",
                    }
                    for i in range(1, 6)
                ],
                "total_questions": 5,
                "estimated_duration_minutes": 8,
                "passing_score": 3,
                "generated_at": _now().isoformat(),
                "model": "dev-placeholder",
                "content_version": 1,
            }, indent=2))

    # Tutorial
    tutorial_path = unit_dir / "tutorial_en.json"
    if not tutorial_path.exists():
        tutorial_path.write_text(json.dumps({
            "unit_id": unit_id,
            "title": f"{title} — Tutorial",
            "grade": 8,
            "subject": subject,
            "lang": "en",
            "sections": [
                {"title": "What to review", "content": f"If you struggled with {title}, start here.", "examples": ["Example 1", "Example 2"], "practice_question": "Now try this on your own."},
            ],
            "common_mistakes": ["Confusing similar terms", "Skipping units in calculation"],
            "generated_at": _now().isoformat(),
            "model": "dev-placeholder",
            "content_version": 1,
        }, indent=2))

    # Meta
    meta_path = unit_dir / "meta.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps({
            "generated_at": _now().isoformat(),
            "model": "dev-placeholder",
            "content_version": 1,
            "langs_built": ["en"],
        }, indent=2))

# ── Step 7: Progress Data ─────────────────────────────────────────────────────

async def setup_progress(
    conn: asyncpg.Connection,
    student_id: uuid.UUID,
    units: list[dict],
) -> None:
    """
    Seed realistic progress data so dashboard, reports, and analytics
    pages all render meaningful content.

    Pattern:
      • Days 1-5 ago: 1 completed+passed session per day (streak = 5)
      • 3 additional passed sessions on older units
      • 2 completed+failed sessions (needs_retry)
      • 1 open in-progress session
      • Lesson views for every passed unit
    """
    _banner("Progress & Analytics Data")

    if not units:
        print("  !  No units found — skipping progress seed")
        return

    # Check if progress already seeded
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM progress_sessions WHERE student_id = $1", student_id
    )
    if existing > 0:
        _skip(f"Progress data ({existing} sessions already exist)")
        return

    # Pick units to use (up to 10)
    work_units = units[:10]

    # ── Passed sessions — last 5 days (streak) ────────────────────────────────
    for day_offset, unit in enumerate(work_units[:5]):
        session_id = uuid.uuid4()
        started = _days_ago(5 - day_offset)
        ended = started + timedelta(minutes=8)
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 started_at, ended_at, score, total_questions, completed, attempt_number, passed)
            VALUES ($1,$2,$3,$4,8,$5,$6,$7,4,5,TRUE,1,TRUE)
            """,
            session_id, student_id, unit["unit_id"], CURRICULUM_ID,
            unit["subject"], started, ended,
        )

    # ── Passed sessions — older units ─────────────────────────────────────────
    for unit in work_units[5:8]:
        session_id = uuid.uuid4()
        started = _days_ago(10)
        ended = started + timedelta(minutes=10)
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 started_at, ended_at, score, total_questions, completed, attempt_number, passed)
            VALUES ($1,$2,$3,$4,8,$5,$6,$7,3,5,TRUE,1,TRUE)
            """,
            session_id, student_id, unit["unit_id"], CURRICULUM_ID,
            unit["subject"], started, ended,
        )

    # ── Failed sessions (needs_retry) ─────────────────────────────────────────
    for unit in work_units[8:10]:
        session_id = uuid.uuid4()
        started = _days_ago(3)
        ended = started + timedelta(minutes=7)
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 started_at, ended_at, score, total_questions, completed, attempt_number, passed)
            VALUES ($1,$2,$3,$4,8,$5,$6,$7,2,5,TRUE,1,FALSE)
            """,
            session_id, student_id, unit["unit_id"], CURRICULUM_ID,
            unit["subject"], started, ended,
        )

    # ── In-progress session (open) ────────────────────────────────────────────
    if len(work_units) > 0:
        open_unit = work_units[0]
        await conn.execute(
            """
            INSERT INTO progress_sessions
                (session_id, student_id, unit_id, curriculum_id, grade, subject,
                 started_at, completed, attempt_number)
            VALUES (gen_random_uuid(),$1,$2,$3,8,$4,NOW(),FALSE,2)
            """,
            student_id, open_unit["unit_id"], CURRICULUM_ID, open_unit["subject"],
        )

    # ── Lesson views ──────────────────────────────────────────────────────────
    for i, unit in enumerate(work_units[:8]):
        started = _days_ago(5 - min(i, 4))
        ended = started + timedelta(minutes=15)
        await conn.execute(
            """
            INSERT INTO lesson_views
                (student_id, unit_id, curriculum_id, duration_s, audio_played,
                 experiment_viewed, started_at, ended_at)
            VALUES ($1,$2,$3,900,$4,FALSE,$5,$6)
            """,
            student_id, unit["unit_id"], CURRICULUM_ID,
            i % 3 == 0,  # every 3rd lesson had audio played
            started, ended,
        )

    _ok("Progress sessions", "5 passed (streak) · 3 passed (older) · 2 failed · 1 open")
    _ok("Lesson views", f"{min(len(work_units), 8)} units viewed")

# ── Step 8: Reset (optional) ──────────────────────────────────────────────────

async def reset_dev_data(conn: asyncpg.Connection) -> None:
    _banner("RESET — Wiping dev accounts and progress data")

    # Progress data (cascades from student delete, but explicit is cleaner)
    student_row = await conn.fetchrow(
        "SELECT student_id FROM students WHERE external_auth_id = $1", DEV_STUDENT_SUB
    )
    if student_row:
        sid = student_row["student_id"]
        await conn.execute("DELETE FROM lesson_views WHERE student_id = $1", sid)
        await conn.execute("DELETE FROM progress_answers WHERE session_id IN (SELECT session_id FROM progress_sessions WHERE student_id = $1)", sid)
        await conn.execute("DELETE FROM progress_sessions WHERE student_id = $1", sid)
        _ok("Progress data wiped")

    await conn.execute("DELETE FROM students WHERE external_auth_id = $1", DEV_STUDENT_SUB)
    await conn.execute("DELETE FROM teachers WHERE external_auth_id IN ($1, $2)", DEV_TEACHER_SUB, DEV_SCHOOL_ADMIN_SUB)
    await conn.execute("DELETE FROM admin_users WHERE email = $1", DEV_ADMIN_EMAIL)
    await conn.execute("DELETE FROM schools WHERE school_id = $1", DEV_SCHOOL_ID)
    _ok("Dev accounts removed — will be recreated on next run")

# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary() -> None:
    _banner("Dev Environment Ready")
    print()
    print("  PORTAL          URL                        LOGIN")
    print("  ─────────────────────────────────────────────────────────────")
    print("  Student         http://localhost:3000/dashboard          /dev-login → Student")
    print("  Teacher         http://localhost:3000/school/dashboard   /dev-login → Teacher")
    print("  School Admin    http://localhost:3000/school/dashboard   /dev-login → School Admin")
    print("  Admin           http://localhost:3000/admin/login        dev.admin@studybuddy.dev")
    print()
    print("  Admin password: DevAdmin1234!")
    print()
    print("  Dev login page: http://localhost:3000/dev-login")
    print()

# ── Entry Point ───────────────────────────────────────────────────────────────

async def main(reset: bool = False) -> None:
    print("\n  StudyBuddy OnDemand — Developer Environment Setup")
    print(f"  Database: {DATABASE_URL.split('@')[-1]}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        if reset:
            await reset_dev_data(conn)

        await setup_school(conn)
        await setup_super_admin(conn)
        await setup_school_admin(conn)
        await setup_teacher(conn)
        student_id = await setup_student(conn)
        units = await setup_curriculum(conn)
        await setup_progress(conn, student_id, units)

    finally:
        await conn.close()

    print_summary()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed dev accounts and test data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe existing dev accounts/progress data before re-seeding.",
    )
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
