#!/usr/bin/env python3
"""
backend/scripts/reset_admin_password.py

Directly resets an admin user's password in the database.
No email or Redis token required — intended for operator use only.

Usage:
    # From backend/ directory:
    python scripts/reset_admin_password.py --email wegofwd2020@gmail.com --password NewPass1!

    # Prompted interactively (hides password input):
    python scripts/reset_admin_password.py --email wegofwd2020@gmail.com
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

import asyncpg
import bcrypt
from dotenv import load_dotenv
import os

_here = Path(__file__).parent.parent
load_dotenv(_here / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def reset(email: str, new_password: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT admin_user_id, role FROM admin_users WHERE email = $1 AND account_status != 'deleted'",
            email,
        )
        if row is None:
            print(f"[reset_admin_password] No active admin found with email: {email}", file=sys.stderr)
            sys.exit(1)

        new_hash = _hash(new_password)
        await conn.execute(
            "UPDATE admin_users SET password_hash = $1 WHERE admin_user_id = $2",
            new_hash,
            row["admin_user_id"],
        )
        print(f"[reset_admin_password] Password updated for {email} (role: {row['role']})")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset an admin user password directly in the DB.")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", default=None, help="New password (omit to be prompted)")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass(f"New password for {args.email}: ")
        confirm = getpass.getpass("Confirm new password: ")
        if password != confirm:
            print("[reset_admin_password] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("[reset_admin_password] Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(reset(args.email, password))


if __name__ == "__main__":
    try:
        main()
    except KeyError as exc:
        print(f"[reset_admin_password] Missing env var: {exc}", file=sys.stderr)
        sys.exit(1)
