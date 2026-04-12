"""
backend/src/demo_leads/service.py

Business logic for demo lead management (Epic 7 — Option C guided tour).

Token format: HS256 JWT with payload { sub: lead_id, name, school_org, iat, exp }.
Decoded client-side in the tour pages to personalise the greeting.
No auth — the token only controls display text, not data access.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from asyncpg import Connection
from jose import jwt

from config import settings
from src.utils.logger import get_logger

log = get_logger("demo_leads")

_ALGO = "HS256"


# ── Token helpers ─────────────────────────────────────────────────────────────


def generate_demo_token(lead_id: str, name: str, school_org: str, ttl_hours: int) -> tuple[str, datetime]:
    """Return (signed_jwt, expires_at) for a personalised tour URL."""
    now = datetime.now(tz=UTC)
    exp = now + timedelta(hours=ttl_hours)
    payload = {
        "sub": lead_id,
        "name": name,
        "school_org": school_org,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.DEMO_TOKEN_SECRET, algorithm=_ALGO)
    return token, exp


# ── Guard checks ──────────────────────────────────────────────────────────────


async def is_country_blocked(conn: Connection, country_code: str | None) -> bool:
    """Return True if country_code is in demo_geo_blocks."""
    if not country_code:
        return False
    row = await conn.fetchrow(
        "SELECT 1 FROM demo_geo_blocks WHERE country_code = $1",
        country_code.upper(),
    )
    return row is not None


async def count_lifetime_leads(conn: Connection, email: str) -> int:
    """Return the total number of demo leads (any status) for this email."""
    return await conn.fetchval(
        "SELECT COUNT(*) FROM demo_leads WHERE LOWER(email) = LOWER($1)",
        email,
    )


async def count_active_leads(conn: Connection, email: str) -> int:
    """Return the number of approved, unexpired leads for this email."""
    return await conn.fetchval(
        """
        SELECT COUNT(*) FROM demo_leads
        WHERE LOWER(email) = LOWER($1)
          AND status = 'approved'
          AND (token_expires_at IS NULL OR token_expires_at > NOW())
        """,
        email,
    )


# ── Write operations ──────────────────────────────────────────────────────────


async def create_lead(
    conn: Connection,
    name: str,
    email: str,
    school_org: str,
    ip_country: str | None,
    ip_address: str | None,
) -> str:
    """Insert a new demo_leads row and return lead_id."""
    lead_id = str(uuid.uuid4())
    await conn.execute(
        """
        INSERT INTO demo_leads (lead_id, name, email, school_org, ip_country, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        uuid.UUID(lead_id),
        name,
        email,
        school_org,
        ip_country,
        ip_address,
    )
    log.info("demo_lead_created lead_id=%s email=%s", lead_id, email)
    return lead_id


async def approve_lead(
    conn: Connection,
    lead_id: str,
    admin_id: str,
    ttl_hours: int,
) -> tuple[str, datetime] | None:
    """
    Approve a pending lead:
      - Generate a signed demo token
      - Update status → approved, set demo_token and token_expires_at
    Returns (token, expires_at) or None if lead not found / already processed.
    """
    row = await conn.fetchrow(
        "SELECT lead_id, name, school_org FROM demo_leads WHERE lead_id = $1 AND status = 'pending'",
        uuid.UUID(lead_id),
    )
    if row is None:
        return None

    token, expires_at = generate_demo_token(lead_id, row["name"], row["school_org"], ttl_hours)

    await conn.execute(
        """
        UPDATE demo_leads
        SET status = 'approved',
            demo_token = $1,
            token_expires_at = $2,
            approved_by = $3,
            approved_at = NOW(),
            updated_at = NOW()
        WHERE lead_id = $4
        """,
        token,
        expires_at,
        uuid.UUID(admin_id),
        uuid.UUID(lead_id),
    )
    log.info("demo_lead_approved lead_id=%s by=%s expires=%s", lead_id, admin_id, expires_at)
    return token, expires_at


async def reject_lead(
    conn: Connection,
    lead_id: str,
    admin_id: str,
    reason: str | None,
) -> bool:
    """Reject a pending lead. Returns True if updated."""
    result = await conn.execute(
        """
        UPDATE demo_leads
        SET status = 'rejected',
            rejected_reason = $1,
            approved_by = $2,
            approved_at = NOW(),
            updated_at = NOW()
        WHERE lead_id = $3 AND status = 'pending'
        """,
        reason,
        uuid.UUID(admin_id),
        uuid.UUID(lead_id),
    )
    updated = result != "UPDATE 0"
    if updated:
        log.info("demo_lead_rejected lead_id=%s by=%s", lead_id, admin_id)
    return updated


# ── Queries ───────────────────────────────────────────────────────────────────


async def list_leads(
    conn: Connection,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return (leads, total_count) ordered by created_at DESC."""
    where = "WHERE status = $1" if status else ""
    args_filter = [status] if status else []

    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM demo_leads {where}", *args_filter  # noqa: S608
    )

    rows = await conn.fetch(
        f"""
        SELECT lead_id::text, name, email, school_org, ip_country,
               status, token_expires_at, approved_at, created_at
        FROM demo_leads
        {where}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
        """,  # noqa: S608
        *args_filter,
    )
    return [dict(r) for r in rows], total


# ── Geo-block helpers ─────────────────────────────────────────────────────────


async def list_geo_blocks(conn: Connection) -> list[dict]:
    rows = await conn.fetch(
        "SELECT country_code, country_name, added_at FROM demo_geo_blocks ORDER BY country_code"
    )
    return [dict(r) for r in rows]


async def add_geo_block(
    conn: Connection,
    country_code: str,
    country_name: str | None,
    admin_id: str,
) -> bool:
    """Insert a geo block. Returns False if already present."""
    result = await conn.execute(
        """
        INSERT INTO demo_geo_blocks (country_code, country_name, added_by)
        VALUES ($1, $2, $3)
        ON CONFLICT (country_code) DO NOTHING
        """,
        country_code.upper(),
        country_name,
        uuid.UUID(admin_id),
    )
    return result != "INSERT 0 0"


async def remove_geo_block(conn: Connection, country_code: str) -> bool:
    """Remove a geo block. Returns False if not present."""
    result = await conn.execute(
        "DELETE FROM demo_geo_blocks WHERE country_code = $1",
        country_code.upper(),
    )
    return result != "DELETE 0"
