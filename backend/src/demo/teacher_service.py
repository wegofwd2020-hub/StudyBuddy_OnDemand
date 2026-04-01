"""
backend/src/demo/teacher_service.py

DB service layer for the demo teacher system.

All functions accept an asyncpg connection and return plain Python dicts/values.
No HTTP awareness — routers own status codes and error responses.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg
from config import settings


async def get_active_demo_teacher_account_by_email(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the active (non-expired, non-revoked) demo_teacher_account for an email."""
    return await conn.fetchrow(
        """
        SELECT id, teacher_id, email, expires_at
        FROM demo_teacher_accounts
        WHERE email = $1
          AND expires_at > NOW()
          AND revoked_at IS NULL
        """,
        email,
    )


async def get_pending_teacher_verification_by_email(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the most recent unused, non-expired teacher verification for an email."""
    return await conn.fetchrow(
        """
        SELECT dtv.id, dtv.request_id, dtv.token, dtv.expires_at
        FROM demo_teacher_verifications dtv
        JOIN demo_teacher_requests dtr ON dtr.id = dtv.request_id
        WHERE dtv.email = $1
          AND dtv.used_at IS NULL
          AND dtv.expires_at > NOW()
          AND dtr.status = 'pending'
        ORDER BY dtv.created_at DESC
        LIMIT 1
        """,
        email,
    )


async def create_demo_teacher_request(
    conn: asyncpg.Connection,
    email: str,
    ip_address: str | None,
    user_agent: str | None,
) -> uuid.UUID:
    """Insert a new demo_teacher_request row and return its id."""
    return await conn.fetchval(
        """
        INSERT INTO demo_teacher_requests (email, ip_address, user_agent, status)
        VALUES ($1, $2, $3, 'pending')
        RETURNING id
        """,
        email,
        ip_address,
        user_agent,
    )


async def create_demo_teacher_verification(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
) -> str:
    """Insert a demo_teacher_verification row and return the token."""
    token = secrets.token_urlsafe(32)
    ttl = settings.DEMO_VERIFICATION_TOKEN_TTL_MINUTES
    expires_at = datetime.now(UTC) + timedelta(minutes=ttl)
    await conn.execute(
        """
        INSERT INTO demo_teacher_verifications (request_id, email, token, expires_at)
        VALUES ($1, $2, $3, $4)
        """,
        request_id,
        email,
        token,
        expires_at,
    )
    return token


async def get_teacher_verification_by_token(
    conn: asyncpg.Connection, token: str
) -> asyncpg.Record | None:
    """Fetch the teacher verification row + request status for a given token."""
    return await conn.fetchrow(
        """
        SELECT dtv.id        AS verif_id,
               dtv.request_id,
               dtv.email,
               dtv.expires_at,
               dtv.used_at,
               dtr.status    AS request_status
        FROM demo_teacher_verifications dtv
        JOIN demo_teacher_requests dtr ON dtr.id = dtv.request_id
        WHERE dtv.token = $1
        """,
        token,
    )


async def count_active_demo_teachers(conn: asyncpg.Connection) -> int:
    """Return the number of currently active demo teacher accounts."""
    return await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM demo_teacher_accounts
        WHERE expires_at > NOW() AND revoked_at IS NULL
        """
    )


def _generate_demo_teacher_password() -> str:
    """Generate a human-readable demo password (e.g. Teach1a2b3c4d)."""
    return "Teach" + secrets.token_hex(4)


async def create_demo_teacher_and_account(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
    password_hash: str,
) -> asyncpg.Record:
    """
    Create a teachers row (auth_provider='demo') and a demo_teacher_accounts row.

    Returns the demo_teacher_accounts record.
    """
    ttl_hours = settings.DEMO_TEACHER_ACCOUNT_TTL_HOURS
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

    demo_external_id = f"demo_teacher:{request_id}"
    teacher_name = email.split("@")[0]

    teacher_row = await conn.fetchrow(
        """
        INSERT INTO teachers (external_auth_id, auth_provider, name, email,
                              account_status)
        VALUES ($1, 'demo', $2, $3, 'active')
        RETURNING teacher_id
        """,
        demo_external_id,
        teacher_name,
        email,
    )
    teacher_id = teacher_row["teacher_id"]

    demo_row = await conn.fetchrow(
        """
        INSERT INTO demo_teacher_accounts
               (request_id, teacher_id, email, password_hash, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, teacher_id, email, expires_at
        """,
        request_id,
        teacher_id,
        email,
        password_hash,
        expires_at,
    )
    return demo_row


async def mark_teacher_verification_used(conn: asyncpg.Connection, verif_id: uuid.UUID) -> None:
    await conn.execute(
        "UPDATE demo_teacher_verifications SET used_at = NOW() WHERE id = $1",
        verif_id,
    )


async def mark_teacher_request_verified(conn: asyncpg.Connection, request_id: uuid.UUID) -> None:
    await conn.execute(
        "UPDATE demo_teacher_requests SET status = 'verified' WHERE id = $1",
        request_id,
    )


async def get_demo_teacher_account_for_login(
    conn: asyncpg.Connection, email: str
) -> asyncpg.Record | None:
    """Return the active demo_teacher_account row for login (includes password_hash)."""
    return await conn.fetchrow(
        """
        SELECT id, teacher_id, email, password_hash, expires_at
        FROM demo_teacher_accounts
        WHERE email = $1
          AND expires_at > NOW()
          AND revoked_at IS NULL
        """,
        email,
    )


async def update_demo_teacher_last_login(
    conn: asyncpg.Connection, demo_account_id: uuid.UUID
) -> None:
    await conn.execute(
        "UPDATE demo_teacher_accounts SET last_login_at = NOW() WHERE id = $1",
        demo_account_id,
    )


async def replace_teacher_verification_token(
    conn: asyncpg.Connection,
    request_id: uuid.UUID,
    email: str,
) -> str:
    """Expire old unused tokens for this request and create a fresh one."""
    await conn.execute(
        """
        UPDATE demo_teacher_verifications
        SET expires_at = NOW()
        WHERE request_id = $1 AND used_at IS NULL AND expires_at > NOW()
        """,
        request_id,
    )
    return await create_demo_teacher_verification(conn, request_id, email)
