#!/usr/bin/env python3
"""
backend/scripts/seed_super_admin.py

Creates (or updates) the super admin account in the database.

Reads credentials from env vars. SUPER_ADMIN_PASSWORD is REQUIRED — there is no
hardcoded default, so a known password can never be shipped to a deploy.

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

# SECURITY: no hardcoded default. A default here previously shipped a known
# super-admin password to the internet-facing demo (seed.sh runs this script
# without setting the env var). The password MUST come from the environment,
# and we reject obviously-weak or previously-leaked values.
_WEAK_PASSWORDS = frozenset({"Admin1234!", "admin", "password", "changeme", "demo"})
SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "")
if not SUPER_ADMIN_PASSWORD:
    sys.exit(
        "[seed_super_admin] SUPER_ADMIN_PASSWORD is required (no default). "
        "Set a strong value, e.g.:\n"
        "  SUPER_ADMIN_PASSWORD='<strong-secret>' python scripts/seed_super_admin.py"
    )
if len(SUPER_ADMIN_PASSWORD) < 12 or SUPER_ADMIN_PASSWORD in _WEAK_PASSWORDS:
    sys.exit(
        "[seed_super_admin] SUPER_ADMIN_PASSWORD is too weak — use at least 12 "
        "characters and not a known default."
    )


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
