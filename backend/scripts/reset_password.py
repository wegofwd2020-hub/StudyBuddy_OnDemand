#!/usr/bin/env python3
"""
backend/scripts/reset_password.py

Reset a user's password directly in the DB across any of the three auth tracks
(admin_users, teachers, students). Locates the account by email, surfaces
ambiguity, and updates only the chosen table.

Usage (from inside the api container):

    # Auto-detect which table the email lives in
    python scripts/reset_password.py --email admin@example.com --password NewPass1!

    # Prompt for password (hidden input)
    python scripts/reset_password.py --email admin@example.com

    # Force a specific table when the email exists in more than one
    python scripts/reset_password.py --email user@example.com --password NewPass1! \\
        --table teachers

    # Force the user to change password on next login (teachers/students only)
    python scripts/reset_password.py --email teacher@school.edu --password Tmp123! \\
        --force-reset

    # Just locate the account, do not change anything
    python scripts/reset_password.py --email user@example.com --lookup

From the host:

    docker compose exec api python scripts/reset_password.py --email ... --password ...
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import bcrypt
from dotenv import load_dotenv

_here = Path(__file__).parent.parent
load_dotenv(_here / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]


# Per-table metadata: which PK column, which extra fields we display, whether
# the table has a `first_login` column, and the auth_provider column (if any).
TABLES = {
    "admin_users": {
        "pk": "admin_user_id",
        "select": "admin_user_id, email, role, account_status",
        "has_first_login": False,
        "has_auth_provider": False,
    },
    "teachers": {
        "pk": "teacher_id",
        "select": "teacher_id, email, role, account_status, first_login, school_id, auth_provider",
        "has_first_login": True,
        "has_auth_provider": True,
    },
    "students": {
        "pk": "student_id",
        "select": "student_id, email, account_status, first_login, school_id, auth_provider",
        "has_first_login": True,
        "has_auth_provider": True,
    },
}


@dataclass
class Match:
    table: str
    pk_value: str
    row: dict


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def _find_matches(conn: asyncpg.Connection, email: str) -> list[Match]:
    matches: list[Match] = []
    for table, meta in TABLES.items():
        sql = (
            f"SELECT {meta['select']} "
            f"FROM {table} "
            f"WHERE email = $1 AND account_status != 'deleted'"
        )
        rows = await conn.fetch(sql, email)
        for row in rows:
            d = dict(row)
            matches.append(Match(table=table, pk_value=str(d[meta["pk"]]), row=d))
    return matches


def _print_matches(matches: list[Match]) -> None:
    for m in matches:
        print(f"  [{m.table}] {m.row}")


async def _update_password(
    conn: asyncpg.Connection,
    table: str,
    pk_value: str,
    new_hash: str,
    *,
    force_reset: bool,
) -> None:
    meta = TABLES[table]
    pk = meta["pk"]

    if meta["has_first_login"]:
        first_login = bool(force_reset)
        await conn.execute(
            f"UPDATE {table} SET password_hash = $1, first_login = $2 "
            f"WHERE {pk}::text = $3",
            new_hash,
            first_login,
            pk_value,
        )
    else:
        # admin_users has no first_login column — ignore --force-reset there.
        await conn.execute(
            f"UPDATE {table} SET password_hash = $1 WHERE {pk}::text = $2",
            new_hash,
            pk_value,
        )


async def run(
    email: str,
    new_password: str | None,
    *,
    table_override: str | None,
    force_reset: bool,
    lookup_only: bool,
) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # RLS bypass — `teachers` and `schools` have FORCE ROW LEVEL SECURITY
        # with a tenant_isolation policy keyed on the `app.current_school_id`
        # session variable. Without setting it, every row is hidden — even
        # from the application role (`studybuddy` is not a superuser and
        # does not carry BYPASSRLS in this environment). Mirrors the
        # `bypass` token already used by login_local_user and the pipeline
        # CLIs (CLAUDE.md pitfalls #23 and #28).
        await conn.execute("SET app.current_school_id = 'bypass'")

        matches = await _find_matches(conn, email)

        if not matches:
            print(f"[reset_password] No active account found with email: {email}",
                  file=sys.stderr)
            return 1

        if lookup_only:
            print(f"[reset_password] Found {len(matches)} match(es) for {email}:")
            _print_matches(matches)
            return 0

        # Resolve the target table.
        if table_override:
            chosen = [m for m in matches if m.table == table_override]
            if not chosen:
                print(
                    f"[reset_password] --table={table_override} but no match in that table. "
                    f"Found in: {sorted({m.table for m in matches})}",
                    file=sys.stderr,
                )
                return 1
            target = chosen[0]
        elif len(matches) > 1:
            print(
                "[reset_password] Email exists in multiple tables — "
                "specify --table to disambiguate. Matches:",
                file=sys.stderr,
            )
            _print_matches(matches)
            return 2
        else:
            target = matches[0]

        # Provider sanity check: a local password is meaningless for Auth0 users.
        # We will still set it (operator override), but warn loudly.
        meta = TABLES[target.table]
        if meta["has_auth_provider"]:
            provider = target.row.get("auth_provider")
            if provider and provider != "local":
                print(
                    f"[reset_password] WARNING: {target.table} row uses auth_provider="
                    f"'{provider}' — local password will be set but the login flow may "
                    f"still go through that provider. Continuing.",
                    file=sys.stderr,
                )

        if new_password is None:
            new_password = getpass.getpass(f"New password for {email} [{target.table}]: ")
            confirm = getpass.getpass("Confirm new password: ")
            if new_password != confirm:
                print("[reset_password] Passwords do not match.", file=sys.stderr)
                return 1

        # Policy: admin ≥ 8, school-provisioned (teachers/students) ≥ 12.
        min_len = 12 if target.table in ("teachers", "students") else 8
        if len(new_password) < min_len:
            print(
                f"[reset_password] Password too short — {target.table} requires "
                f"≥ {min_len} characters.",
                file=sys.stderr,
            )
            return 1
        if len(new_password.encode()) > 72:
            print(
                "[reset_password] Password exceeds bcrypt's 72-byte limit.",
                file=sys.stderr,
            )
            return 1

        new_hash = _hash(new_password)
        await _update_password(
            conn,
            target.table,
            target.pk_value,
            new_hash,
            force_reset=force_reset,
        )

        first_login_note = ""
        if meta["has_first_login"]:
            first_login_note = (
                "  [first_login=TRUE — user must change at next login]"
                if force_reset else
                "  [first_login=FALSE — user can sign in directly]"
            )
        print(
            f"[reset_password] Password updated.  "
            f"table={target.table}  id={target.pk_value}  email={email}"
            f"{first_login_note}"
        )
        return 0
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reset a user's password in any of admin_users / teachers / students. "
            "Looks up the account by email and updates only the resolved row."
        ),
    )
    parser.add_argument("--email", required=True, help="Account email address")
    parser.add_argument(
        "--password",
        default=None,
        help="New password (omit to be prompted; input is hidden)",
    )
    parser.add_argument(
        "--table",
        choices=sorted(TABLES.keys()),
        default=None,
        help="Force the target table when the email exists in more than one",
    )
    parser.add_argument(
        "--force-reset",
        action="store_true",
        help=(
            "Set first_login=TRUE so the user must change the password on next "
            "login. Applies to teachers/students only (ignored for admin_users)."
        ),
    )
    parser.add_argument(
        "--lookup",
        action="store_true",
        help="Locate the account(s) for this email and exit without changing anything",
    )
    args = parser.parse_args()

    rc = asyncio.run(
        run(
            email=args.email,
            new_password=args.password,
            table_override=args.table,
            force_reset=args.force_reset,
            lookup_only=args.lookup,
        )
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
