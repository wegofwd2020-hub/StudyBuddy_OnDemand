#!/usr/bin/env python
# =============================================================================
# backend/scripts/purge_account.py
#
# SUPER-ADMIN / OPERATOR test utility: HARD-delete a single school account
# (teacher or student) by email — completely, leaving no trace. No soft delete,
# no deactivation timestamp, no archive, no retention.
#
# ⚠️  This DELIBERATELY BYPASSES the compliant deletion flow in ADR-005
#     Decision 3 (soft delete → deactivate + archive → FERPA retention). It is a
#     TESTING escape hatch so a tester can wipe an account and re-add the same
#     email via the admin screens on the next run. It is NOT the product's
#     "Delete" behaviour and must never be wired into the school-admin UI.
#
#     DO NOT run against a database holding real customer / student records — it
#     destroys educational records irrecoverably.
#
# What it removes:
#   - the teachers/students row for the email, and
#   - everything that hangs off it via ON DELETE CASCADE (enrolments, progress,
#     sessions, answers, feedback, classroom_students, teacher_capabilities, …).
#   FK columns declared ON DELETE SET NULL (audit refs like created_by /
#   granted_by / reviewed_by) are nulled — the account row itself is gone.
#   FK children declared RESTRICT / NO ACTION (e.g. student_teacher_assignments,
#   curriculum_definitions.submitted_by) are cleared first so the delete can
#   proceed. The blocking-child set is discovered from pg_constraint at runtime,
#   so it stays correct as the schema grows.
#
# Safety:
#   - DRY-RUN by default: runs inside a transaction and ROLLS BACK, printing the
#     rows it WOULD delete. Nothing is persisted.
#   - Pass --commit to persist.
#
# Usage (inside the api container):
#   # Dry-run — see what would go:
#   docker compose exec api python scripts/purge_account.py --email foo@example.com
#   # Execute for real:
#   docker compose exec api python scripts/purge_account.py --email foo@example.com --commit
# =============================================================================

import argparse
import asyncio
import os

import asyncpg


async def _resolve_account(
    conn: asyncpg.Connection, email: str
) -> tuple[str, str, str, asyncpg.Record] | None:
    """Find the account by email. Returns (kind, table, id_col, row) or None.

    Teacher and student emails are globally UNIQUE and an account is teacher XOR
    student (ADR-005), so at most one table matches.
    """
    for kind, table, id_col in (
        ("teacher", "teachers", "teacher_id"),
        ("student", "students", "student_id"),
    ):
        row = await conn.fetchrow(f"SELECT * FROM {table} WHERE email = $1", email)
        if row:
            return kind, table, id_col, row
    return None


async def _blocking_children(conn: asyncpg.Connection, parent_table: str) -> list[tuple[str, str]]:
    """(child_table, child_col) for every FK into parent_table whose ON DELETE is
    RESTRICT ('r') or NO ACTION ('a') — the ones that must be cleared by hand.
    CASCADE / SET NULL / SET DEFAULT resolve themselves on the parent delete.
    """
    rows = await conn.fetch(
        """
        SELECT c.conrelid::regclass::text AS child_table,
               a.attname                  AS child_col
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
        WHERE c.confrelid = $1::regclass
          AND c.contype = 'f'
          AND c.confdeltype IN ('r', 'a')
        ORDER BY child_table
        """,
        parent_table,
    )
    return [(r["child_table"], r["child_col"]) for r in rows]


async def main() -> None:
    ap = argparse.ArgumentParser(description="Hard-delete a school account by email (test only).")
    ap.add_argument("--email", required=True, help="email of the teacher/student to purge")
    ap.add_argument("--commit", action="store_true", help="persist the delete (default: dry-run)")
    args = ap.parse_args()

    url = os.environ.get("DIRECT_DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DIRECT_DB_URL / DATABASE_URL not set")

    conn = await asyncpg.connect(url)
    try:
        # RLS bypass — teachers/students are tenant-isolated (migration 0028).
        await conn.execute("SET app.current_school_id = 'bypass'")

        tr = conn.transaction()
        await tr.start()
        mode = "COMMIT MODE" if args.commit else "DRY-RUN (will roll back)"
        print(f"=== {mode} — purge {args.email!r} ===")

        acct = await _resolve_account(conn, args.email)
        if acct is None:
            print(f"  no teacher or student found with email {args.email!r}")
            await tr.rollback()
            return

        kind, table, id_col, row = acct
        rd = dict(row)
        aid = rd[id_col]
        print(
            f"  found {kind}: {id_col}={aid} school_id={rd.get('school_id')} "
            f"role={rd.get('role', '-')} status={rd['account_status']} name={rd.get('name')!r}"
        )

        # Non-blocking warning: purging the last school_admin orphans the school.
        if kind == "teacher" and rd.get("role") == "school_admin":
            remaining = await conn.fetchval(
                "SELECT count(*) FROM teachers WHERE school_id = $1 AND role = 'school_admin'",
                rd["school_id"],
            )
            if remaining <= 1:
                print(
                    f"  ⚠️  WARNING: last school_admin for school {rd['school_id']} — "
                    "the school will have NO admin after this purge."
                )

        # Clear RESTRICT / NO ACTION children that would otherwise block the delete.
        for child_table, child_col in await _blocking_children(conn, table):
            res = await conn.execute(f"DELETE FROM {child_table} WHERE {child_col} = $1", aid)
            print(f"  clear blocking {child_table}.{child_col:24} -> {res}")

        # Delete the account row; CASCADE children go with it, SET NULL refs nulled.
        res = await conn.execute(f"DELETE FROM {table} WHERE {id_col} = $1", aid)
        print(f"  DELETE {table:28} -> {res}")

        if args.commit:
            await tr.commit()
            print("=== COMMITTED — account purged (no trace); email is free to re-add ===")
        else:
            await tr.rollback()
            print("=== ROLLED BACK — pass --commit to persist ===")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
