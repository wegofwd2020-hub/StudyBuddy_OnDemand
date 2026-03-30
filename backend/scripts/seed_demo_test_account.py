#!/usr/bin/env python3
"""
backend/scripts/seed_demo_test_account.py

Creates (or refreshes) a persistent demo test account used for manual QA,
demos, and integration testing.

    Email    : demo-test@studybuddy.dev
    Password : DemoTest-2026!
    TTL      : 30 days from now (re-running extends it)

The script is fully idempotent:
  - If the demo_requests / students / demo_accounts rows already exist they are
    updated in-place (password hash and expiry refreshed, not duplicated).
  - Safe to run on every deploy or whenever the account needs refreshing.

Usage (inside the api container):
    python scripts/seed_demo_test_account.py

Or from the repo root:
    docker compose exec api python scripts/seed_demo_test_account.py

Optional flags:
    --ttl-days N     Override 30-day default (e.g. --ttl-days 7)
    --dry-run        Print what would happen without writing to the DB
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

import asyncpg
import bcrypt

# Allow running from repo root or from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Constants ─────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo-test@studybuddy.dev"
DEMO_PASSWORD = "DemoTest-2026!"
DEMO_GRADE = 8
DEMO_LOCALE = "en"

# Connect directly to PostgreSQL; PgBouncer in transaction-pooling mode drops
# asyncpg prepared statements silently.
_raw_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://studybuddy:studybuddy_dev@db:5432/studybuddy",
)
DATABASE_URL = _raw_url.replace("@pgbouncer:", "@db:")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _hash_password(password: str) -> str:
    """bcrypt hash — runs synchronously (fine in a one-shot script)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _fmt(val: object) -> str:
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M UTC")
    return str(val)


# ── Core logic ────────────────────────────────────────────────────────────────


async def seed(ttl_days: int, dry_run: bool) -> None:
    expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
    password_hash = _hash_password(DEMO_PASSWORD)

    if dry_run:
        print("[dry-run] Would upsert demo test account:")
        print(f"  email      : {DEMO_EMAIL}")
        print(f"  expires_at : {_fmt(expires_at)}")
        print(f"  ttl_days   : {ttl_days}")
        return

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                # ── Check for an existing demo_account by email ───────────────
                existing = await conn.fetchrow(
                    """
                    SELECT id, student_id, request_id, email, expires_at
                    FROM demo_accounts
                    WHERE email = $1
                    """,
                    DEMO_EMAIL,
                )

                if existing:
                    # Account already exists — refresh password and expiry only.
                    demo_row = await conn.fetchrow(
                        """
                        UPDATE demo_accounts
                           SET password_hash = $1,
                               expires_at    = $2,
                               revoked_at    = NULL,
                               revoked_by    = NULL,
                               extended_at   = NOW()
                         WHERE email = $3
                         RETURNING id, student_id, email, expires_at
                        """,
                        password_hash,
                        expires_at,
                        DEMO_EMAIL,
                    )
                    print(f"  demo_requests : existing row {existing['request_id']}")
                    print(f"  students      : existing row {existing['student_id']}")
                else:
                    # Fresh create: demo_requests → students → demo_accounts.

                    # 1. demo_requests — no unique email constraint; always insert fresh.
                    request_id = await conn.fetchval(
                        """
                        INSERT INTO demo_requests
                            (email, ip_address, user_agent, status)
                        VALUES ($1, 'seed-script', 'seed_demo_test_account.py', 'verified')
                        RETURNING id
                        """,
                        DEMO_EMAIL,
                    )
                    print(f"  demo_requests : created  {request_id}")

                    # 2. students — email is unique; skip on conflict (may already
                    #    exist from a prior partial run), then fetch by email.
                    demo_external_id = f"demo:{request_id}"
                    student_id = await conn.fetchval(
                        """
                        INSERT INTO students
                            (external_auth_id, auth_provider, name,
                             email, grade, locale, account_status)
                        VALUES ($1, 'demo', 'Demo Test Student', $2, $3, $4, 'active')
                        ON CONFLICT (email) DO NOTHING
                        RETURNING student_id
                        """,
                        demo_external_id,
                        DEMO_EMAIL,
                        DEMO_GRADE,
                        DEMO_LOCALE,
                    )
                    if student_id is None:
                        student_id = await conn.fetchval(
                            "SELECT student_id FROM students WHERE email = $1",
                            DEMO_EMAIL,
                        )
                        print(f"  students      : existing row {student_id} (re-linked)")
                    else:
                        print(f"  students      : created  {student_id}")

                    # 3. demo_accounts — insert fresh (we checked it doesn't exist).
                    demo_row = await conn.fetchrow(
                        """
                        INSERT INTO demo_accounts
                            (request_id, student_id, email, password_hash, expires_at)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id, student_id, email, expires_at
                        """,
                        request_id,
                        student_id,
                        DEMO_EMAIL,
                        password_hash,
                        expires_at,
                    )

                print()
                print("Demo test account ready:")
                print(f"  demo_account_id : {demo_row['id']}")
                print(f"  student_id      : {demo_row['student_id']}")
                print(f"  email           : {demo_row['email']}")
                print(f"  expires_at      : {_fmt(demo_row['expires_at'])}")
                print(f"  password        : {DEMO_PASSWORD}")
    finally:
        await pool.close()


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed or refresh the persistent demo test account"
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=30,
        metavar="N",
        help="Days until the account expires (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to the DB",
    )
    args = parser.parse_args()

    if args.ttl_days < 1 or args.ttl_days > 365:
        print("Error: --ttl-days must be between 1 and 365.", file=sys.stderr)
        sys.exit(1)

    print(f"Seeding demo test account (ttl={args.ttl_days}d, dry_run={args.dry_run})…")
    asyncio.run(seed(args.ttl_days, args.dry_run))


if __name__ == "__main__":
    main()
