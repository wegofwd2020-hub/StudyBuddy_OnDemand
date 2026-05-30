#!/usr/bin/env python
# =============================================================================
# backend/scripts/teardown_demo_accounts.py
#
# DEMO-ONLY destructive reset: deletes every tenant account (schools + their
# teachers + students) and every public demo-request lead, while PRESERVING the
# super_admin (admin_users) and the platform content catalog
# (curricula WHERE owner_type='platform').
#
# Intended target: the demo VPS (demo.usestudybuddy.com). Do NOT run against a
# database that holds real customer data.
#
# Safety:
#   - DRY-RUN by default: runs the deletes inside a transaction and ROLLS BACK,
#     printing the row counts it *would* delete. Nothing is persisted.
#   - To actually delete, set DELETE_DEMO_COMMIT=1.
#
# Usage (inside the api container on the VPS):
#   # 1) Dry-run — see what would go:
#   docker compose exec api python scripts/teardown_demo_accounts.py
#   # 2) Execute for real:
#   docker compose exec -e DELETE_DEMO_COMMIT=1 api python scripts/teardown_demo_accounts.py
#
# FK order below was derived from pg_constraint (confdeltype):
#   teachers <- student_teacher_assignments = RESTRICT  -> clear first
#   teachers <- curriculum_definitions       = NO ACTION -> clear first
#   schools  <- teachers                      = NO ACTION -> delete teachers before schools
#   schools  <- students                      = SET NULL  -> delete students explicitly
#   schools  <- curricula / pipeline_jobs     = SET NULL  -> platform curricula survive
# Everything else into students/teachers/schools is ON DELETE CASCADE.
# =============================================================================

import asyncio
import os

import asyncpg

COMMIT = os.environ.get("DELETE_DEMO_COMMIT") == "1"

# Deleted in this exact order to satisfy the FK rules documented above.
DELETE_ORDER = [
    "student_teacher_assignments",
    "curriculum_definitions",
    "demo_verifications",
    "demo_accounts",
    "demo_requests",
    "demo_teacher_verifications",
    "demo_teacher_accounts",
    "demo_teacher_requests",
    "students",
    "teachers",
    "schools",
]

PRESERVED = [
    ("admin_users (super_admin)", "SELECT count(*) FROM admin_users"),
    ("platform curricula kept", "SELECT count(*) FROM curricula WHERE owner_type='platform'"),
]


async def main() -> None:
    url = os.environ.get("DIRECT_DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DIRECT_DB_URL / DATABASE_URL not set")

    conn = await asyncpg.connect(url)
    try:
        # RLS bypass — schools/teachers/students are tenant-isolated (migration 0028).
        await conn.execute("SET app.current_school_id = 'bypass'")

        tr = conn.transaction()
        await tr.start()
        print(f"=== {'COMMIT MODE' if COMMIT else 'DRY-RUN (will roll back)'} ===")
        for table in DELETE_ORDER:
            result = await conn.execute(f"DELETE FROM {table}")
            print(f"  DELETE {table:32} -> {result}")

        print("--- preserved ---")
        for label, query in PRESERVED:
            print(f"  {label:28} = {await conn.fetchval(query)}")

        if COMMIT:
            await tr.commit()
            print("=== COMMITTED — demo accounts deleted ===")
        else:
            await tr.rollback()
            print("=== ROLLED BACK — set DELETE_DEMO_COMMIT=1 to persist ===")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
