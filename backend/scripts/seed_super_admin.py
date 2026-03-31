#!/usr/bin/env python3
"""
backend/scripts/seed_super_admin.py

Creates (or updates) the super admin account in the database.

Reads credentials from env vars; falls back to the defaults in .env.

Usage:
    # From backend/ directory:
    python scripts/seed_super_admin.py

    # Override email / password at runtime:
    SUPER_ADMIN_EMAIL=other@email.com SUPER_ADMIN_PASSWORD=NewPass1! python scripts/seed_super_admin.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import bcrypt
from dotenv import load_dotenv

# Load .env from backend/ (works whether you run from backend/ or project root)
_here = Path(__file__).parent.parent
load_dotenv(_here / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
SUPER_ADMIN_EMAIL = os.environ.get("SUPER_ADMIN_EMAIL", "wegofwd2020@gmail.com")
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "Admin1234!")


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        password_hash = _hash(SUPER_ADMIN_PASSWORD)

        result = await conn.execute(
            """
            INSERT INTO admin_users (email, password_hash, role, account_status)
            VALUES ($1, $2, 'super_admin', 'active')
            ON CONFLICT (email) DO UPDATE
                SET password_hash  = EXCLUDED.password_hash,
                    role           = 'super_admin',
                    account_status = 'active'
            """,
            SUPER_ADMIN_EMAIL,
            password_hash,
        )

        action = "created" if result == "INSERT 0 1" else "updated"
        print(f"[seed_super_admin] Super admin {action}: {SUPER_ADMIN_EMAIL}")
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyError as exc:
        print(f"[seed_super_admin] Missing env var: {exc}", file=sys.stderr)
        sys.exit(1)
