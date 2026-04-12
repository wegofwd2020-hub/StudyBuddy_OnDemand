"""
scripts/seed_demo.py — Seed the Riverside Academy demo school.

Creates a realistic demo environment with 3 teachers, 30 students,
4 classrooms, and curriculum for grades 8–10.  Safe to run multiple times
(idempotent via ON CONFLICT DO NOTHING).

Usage:
    # Seed (idempotent — skips rows that already exist):
    docker compose exec api python scripts/seed_demo.py

    # Full reset (wipe then reseed):
    docker compose exec api python scripts/seed_demo.py --reset

Credentials printed at the end.  All users share the password: Demo2026!
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from src.admin.demo_seed import (
    DEMO_PASSWORD,
    DEMO_SCHOOL_NAME,
    _CLASSROOMS,
    _STUDENTS,
    _TEACHERS,
    reset_demo,
    seed_demo,
    wipe_demo,
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy@localhost:5432/studybuddy",
)


async def _run(do_reset: bool) -> None:
    conn = await asyncpg.connect(DB_URL)
    # Bypass RLS — seed operates across school boundaries as a privileged admin.
    await conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")

    try:
        if do_reset:
            print(f"Wiping {DEMO_SCHOOL_NAME} demo data…")
            await wipe_demo(conn)
            print("Done. Re-seeding…")
            counts = await seed_demo(conn)
        else:
            print(f"Seeding {DEMO_SCHOOL_NAME} (idempotent)…")
            counts = await seed_demo(conn)
    finally:
        await conn.close()

    print()
    print("─" * 60)
    print(f"  {DEMO_SCHOOL_NAME} — demo school seeded")
    print("─" * 60)
    print(f"  Schools:    {counts['schools']} inserted")
    print(f"  Teachers:   {counts['teachers']} inserted")
    print(f"  Students:   {counts['students']} inserted")
    print(f"  Curricula:  {counts['curricula']} inserted")
    print(f"  Units:      {counts['units']} inserted")
    print(f"  Classrooms: {counts['classrooms']} inserted")
    print()
    print("  Shared password for all demo accounts:")
    print(f"    {DEMO_PASSWORD}")
    print()
    print("  Teachers:")
    for t in _TEACHERS:
        print(f"    [{t['role']:<12}]  {t['email']}")
    print()
    print("  Students (sample):")
    for s in _STUDENTS[:5]:
        from src.admin.demo_seed import _student_email
        print(f"    [grade {s['grade']}]  {_student_email(s['name'])}")
    print(f"    … and {len(_STUDENTS) - 5} more")
    print()
    print("  Classrooms:")
    for cl in _CLASSROOMS:
        print(f"    {cl['name']}")
    print()
    print("  Login URL:  http://localhost:3000/school/login")
    print("─" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Riverside Academy demo school."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe all existing demo data before seeding (destructive).",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.reset))


if __name__ == "__main__":
    main()
