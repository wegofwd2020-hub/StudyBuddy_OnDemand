#!/usr/bin/env python3
"""
backend/scripts/create_admin.py

Create the first admin user (or any subsequent admin) interactively.

Usage:
    python backend/scripts/create_admin.py --email admin@example.com --role super_admin

Prompts for password interactively; never accepts password via CLI argument or env var.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import os

# Allow running from repo root or backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncpg

VALID_ROLES = ("developer", "tester", "product_admin", "super_admin")


async def create_admin(email: str, role: str, password: str) -> None:
    from config import settings
    from src.auth.service import hash_password

    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=2)
    try:
        hashed = await hash_password(password)
        row = await pool.fetchrow(
            """
            INSERT INTO admin_users (email, password_hash, role, account_status)
            VALUES ($1, $2, $3, 'active')
            ON CONFLICT (email) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    role          = EXCLUDED.role
            RETURNING admin_user_id, email, role
            """,
            email,
            hashed,
            role,
        )
        print(f"Admin user created/updated:")
        print(f"  admin_user_id : {row['admin_user_id']}")
        print(f"  email         : {row['email']}")
        print(f"  role          : {row['role']}")
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a StudyBuddy admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument(
        "--role",
        required=True,
        choices=VALID_ROLES,
        help="Admin role",
    )
    args = parser.parse_args()

    print(f"Creating admin: {args.email} ({args.role})")
    password = getpass.getpass("Password (min 12 chars): ")
    if len(password) < 12:
        print("Error: Password must be at least 12 characters.", file=sys.stderr)
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(create_admin(args.email, args.role, password))


if __name__ == "__main__":
    main()
