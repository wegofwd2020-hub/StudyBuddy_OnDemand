"""
backend/src/demo/service.py

DB service layer for the demo student system.

All functions accept an asyncpg connection and return plain Python dicts/values.
No HTTP awareness — routers own status codes and error responses.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
from config import settings

# ── Request + verification ────────────────────────────────────────────────────


async def get_active_demo_account_by_email(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the active (non-expired, non-revoked) demo_account for an email."""
    return await conn.fetchrow(
        """
        SELECT id, student_id, email, expires_at
        FROM demo_accounts
        WHERE email = $1
          AND expires_at > NOW()
          AND revoked_at IS NULL
        """,
        email,
    )


async def get_pending_verification_by_email(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the most recent unused, non-expired verification for an email."""
    return await conn.fetchrow(
        """
        SELECT dv.id, dv.request_id, dv.token, dv.expires_at
        FROM demo_verifications dv
        JOIN demo_requests dr ON dr.id = dv.request_id
        WHERE dv.email = $1
          AND dv.used_at IS NULL
          AND dv.expires_at > NOW()
          AND dr.status = 'pending'
        ORDER BY dv.created_at DESC
        LIMIT 1
        """,
        email,
    )


async def create_demo_request(
    conn: asyncpg.Connection,
    email: str,
    ip_address: str | None,
    user_agent: str | None,
) -> uuid.UUID:
    """Insert a new demo_request row and return its id."""
    return await conn.fetchval(
        """
        INSERT INTO demo_requests (email, ip_address, user_agent, status)
        VALUES ($1, $2, $3, 'pending')
        RETURNING id
        """,
        email,
        ip_address,
        user_agent,
    )


def _generate_verification_token() -> str:
    """Generate a cryptographically random URL-safe verification token."""
    return secrets.token_urlsafe(32)


async def create_demo_verification(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
) -> str:
    """Insert a demo_verification row and return the token."""
    token = _generate_verification_token()
    ttl = settings.DEMO_VERIFICATION_TOKEN_TTL_MINUTES
    expires_at = datetime.now(UTC) + timedelta(minutes=ttl)
    await conn.execute(
        """
        INSERT INTO demo_verifications (request_id, email, token, expires_at)
        VALUES ($1, $2, $3, $4)
        """,
        request_id,
        email,
        token,
        expires_at,
    )
    return token


async def get_verification_by_token(
    conn: asyncpg.Connection, token: str
) -> asyncpg.Record | None:
    """Fetch the verification row + request status for a given token."""
    return await conn.fetchrow(
        """
        SELECT dv.id        AS verif_id,
               dv.request_id,
               dv.email,
               dv.expires_at,
               dv.used_at,
               dr.status    AS request_status
        FROM demo_verifications dv
        JOIN demo_requests dr ON dr.id = dv.request_id
        WHERE dv.token = $1
        """,
        token,
    )


async def count_active_demos(conn: asyncpg.Connection) -> int:
    """Return the number of currently active (non-expired, non-revoked) demo accounts."""
    return await conn.fetchval(
        "SELECT COUNT(*) FROM demo_accounts WHERE expires_at > NOW() AND revoked_at IS NULL"
    )


def _generate_demo_password() -> str:
    """Generate a human-readable demo password (e.g. Study1a2b3c4d)."""
    return "Study" + secrets.token_hex(4)


async def create_demo_student_and_account(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
    from_password: str,  # caller must pass the *plaintext* password for hashing upstream
    password_hash: str,
) -> asyncpg.Record:
    """
    Create a students row (auth_provider='demo') and a demo_accounts row.

    Returns the demo_accounts record.
    """
    ttl_hours = settings.DEMO_ACCOUNT_TTL_HOURS
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

    demo_external_id = f"demo:{request_id}"
    student_name = email.split("@")[0]

    student_row = await conn.fetchrow(
        """
        INSERT INTO students (external_auth_id, auth_provider, name, email,
                              grade, locale, account_status)
        VALUES ($1, 'demo', $2, $3, 8, 'en', 'active')
        RETURNING student_id
        """,
        demo_external_id,
        student_name,
        email,
    )
    student_id = student_row["student_id"]

    demo_row = await conn.fetchrow(
        """
        INSERT INTO demo_accounts (request_id, student_id, email, password_hash, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, student_id, email, expires_at
        """,
        request_id,
        student_id,
        email,
        password_hash,
        expires_at,
    )
    return demo_row


async def mark_verification_used(
    conn: asyncpg.Connection, verif_id: uuid.UUID
) -> None:
    await conn.execute(
        "UPDATE demo_verifications SET used_at = NOW() WHERE id = $1",
        verif_id,
    )


async def mark_request_verified(
    conn: asyncpg.Connection, request_id: uuid.UUID
) -> None:
    await conn.execute(
        "UPDATE demo_requests SET status = 'verified' WHERE id = $1",
        request_id,
    )


# ── Login helpers ─────────────────────────────────────────────────────────────


async def get_demo_account_for_login(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the active demo_account row for login (includes password_hash)."""
    return await conn.fetchrow(
        """
        SELECT id, student_id, email, password_hash, expires_at
        FROM demo_accounts
        WHERE email = $1
          AND expires_at > NOW()
          AND revoked_at IS NULL
        """,
        email,
    )


async def update_last_login(
    conn: asyncpg.Connection, demo_account_id: uuid.UUID
) -> None:
    await conn.execute(
        "UPDATE demo_accounts SET last_login_at = NOW() WHERE id = $1",
        demo_account_id,
    )


# ── Resend helpers ────────────────────────────────────────────────────────────


async def replace_verification_token(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
) -> str:
    """
    Expire old unused tokens for this request and create a fresh one.
    Returns the new token.
    """
    # Soft-expire the old tokens so they're no longer valid
    await conn.execute(
        """
        UPDATE demo_verifications
        SET expires_at = NOW()
        WHERE request_id = $1 AND used_at IS NULL AND expires_at > NOW()
        """,
        request_id,
    )
    return await create_demo_verification(conn, request_id, email)
