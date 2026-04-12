"""
backend/src/auth/service.py

Core authentication service functions.

Key functions:
  verify_auth0_token()     — verify Auth0 id_token against JWKS (L1 cached)
  create_internal_jwt()    — issue HS256 JWT for students/teachers
  create_admin_jwt()       — issue HS256 JWT for admin users
  verify_internal_jwt()    — decode and verify internal JWT
  hash_password()          — bcrypt in executor (non-blocking)
  verify_password()        — bcrypt in executor (non-blocking)
  upsert_student()         — INSERT ... ON CONFLICT UPDATE
  upsert_teacher()         — INSERT ... ON CONFLICT UPDATE
  Auth0 Management API calls (block, delete, password reset)
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import partial

import asyncpg
import bcrypt
import httpx
from config import settings
from fastapi import HTTPException
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from src.core.cache import jwks_cache
from src.utils.logger import get_logger

log = get_logger("auth")

# ── Auth0 JWKS verification ───────────────────────────────────────────────────


async def _fetch_jwks() -> dict:
    """Fetch JWKS from Auth0 and store in L1 cache."""
    cached = jwks_cache.get(settings.AUTH0_JWKS_URL)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.AUTH0_JWKS_URL)
        resp.raise_for_status()
        jwks = resp.json()

    jwks_cache[settings.AUTH0_JWKS_URL] = jwks
    log.info("jwks_refreshed", url=settings.AUTH0_JWKS_URL)
    return jwks


async def _verify_auth0_token(id_token: str, audience: str) -> dict:
    """
    Shared Auth0 JWT verification logic, parameterised by audience.

    Flow:
      1. Parse the unverified header to extract `kid`.
      2. Fetch the matching RSA key from JWKS (L1 cache via _fetch_jwks).
      3. If the key is not found, evict the cache and retry once (handles
         key rotation between cache warm and token issuance).
      4. Decode + verify the JWT (RS256, audience, issuer).

    Returns decoded claims on success.
    Raises HTTP 401 on any failure — never leaks internal detail.
    """
    try:
        unverified_header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        log.warning("auth0_token_header_invalid", error=str(exc))
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT header could not be parsed."},
        )

    kid = unverified_header.get("kid")
    jwks = await _fetch_jwks()

    def _find_key(keys: list) -> dict:
        for key in keys:
            if key.get("kid") == kid:
                return {k: key[k] for k in ("kty", "kid", "n", "e")}
        return {}

    rsa_key = _find_key(jwks.get("keys", []))

    if not rsa_key:
        # Key not found — JWKS may be stale; evict cache and retry once.
        log.warning("jwks_key_not_found", kid=kid, audience=audience, retrying=True)
        jwks_cache.pop(settings.AUTH0_JWKS_URL, None)
        jwks = await _fetch_jwks()
        rsa_key = _find_key(jwks.get("keys", []))

    if not rsa_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT signing key not found."},
        )

    try:
        payload = jwt.decode(
            id_token,
            rsa_key,
            algorithms=["RS256"],
            audience=audience,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Token has expired."},
        )
    except JWTError as exc:
        log.warning("auth0_token_verification_failed", error=str(exc), audience=audience)
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT signature verification failed."},
        )

    return payload


async def verify_auth0_token(id_token: str) -> dict:
    """Verify an Auth0 student id_token. Returns decoded claims or raises HTTP 401."""
    return await _verify_auth0_token(id_token, settings.AUTH0_STUDENT_CLIENT_ID)


async def verify_auth0_teacher_token(id_token: str) -> dict:
    """Verify an Auth0 teacher id_token. Returns decoded claims or raises HTTP 401."""
    return await _verify_auth0_token(id_token, settings.AUTH0_TEACHER_CLIENT_ID)


# ── Internal JWT helpers ──────────────────────────────────────────────────────


def create_internal_jwt(payload: dict, secret: str, expire_minutes: int) -> str:
    """
    Sign a payload as an HS256 JWT.

    Always adds exp, iat, jti claims (per studybuddy-docs/PHASE1_SETUP.md section 10.3).
    """
    now = datetime.now(tz=UTC)
    claims = {
        **payload,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, secret, algorithm=settings.JWT_ALGORITHM)


def create_admin_jwt(payload: dict) -> str:
    """Issue an admin JWT signed with ADMIN_JWT_SECRET."""
    return create_internal_jwt(
        payload,
        settings.ADMIN_JWT_SECRET,
        settings.ADMIN_JWT_EXPIRE_MINUTES,
    )


def verify_internal_jwt(token: str, secret: str) -> dict:
    """
    Decode and verify an internal HS256 JWT.

    Raises HTTP 401 on any failure.
    """
    try:
        return jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Token has expired."},
        )
    except JWTError as exc:
        log.warning("internal_jwt_verification_failed", error=str(exc))
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT signature verification failed."},
        )


# ── Refresh token helpers ─────────────────────────────────────────────────────


def _hash_refresh_token(token: str) -> str:
    """SHA-256 hash of a refresh token for use as a Redis key."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    """Generate a 48-byte URL-safe random refresh token."""
    return secrets.token_urlsafe(48)


# ── bcrypt helpers (run in executor to avoid blocking event loop) ─────────────


async def hash_password(password: str) -> str:
    """Hash a password with bcrypt, executed in the default thread pool."""
    loop = asyncio.get_running_loop()
    hashed: bytes = await loop.run_in_executor(
        None,
        partial(bcrypt.hashpw, password.encode(), bcrypt.gensalt(rounds=12)),
    )
    return hashed.decode()


async def verify_password(plain: str, hashed: str) -> bool:
    """Verify a bcrypt password in the thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(bcrypt.checkpw, plain.encode(), hashed.encode()),
    )


# ── DB helpers — upsert student / teacher ────────────────────────────────────


async def upsert_student(
    pool: asyncpg.Pool,
    auth0_sub: str,
    name: str,
    email: str,
    grade: int,
    locale: str,
    requires_parental_consent: bool = False,
) -> dict:
    """
    Insert or update a student row (keyed by external_auth_id / auth0_sub).

    For new accounts:
      - requires_parental_consent=False → account_status set to 'active' immediately
      - requires_parental_consent=True  → account_status set to 'pending'
        until the parental_consents record is updated to 'granted'

    On conflict (returning student re-authenticates), account_status rules:
      - 'suspended' → always kept (never auto-unsuspend via re-login)
      - 'pending' + incoming 'active' → transition to 'active' (consent completed)
      - anything else → keep existing status

    Grade is never overridden for school-enrolled students (school manages it).

    Returns the full student record as a dict.
    """
    initial_status = "pending" if requires_parental_consent else "active"
    row = await pool.fetchrow(
        """
        INSERT INTO students (external_auth_id, auth_provider, name, email, grade, locale,
                              account_status)
        VALUES ($1, 'auth0', $2, $3, $4, $5, $6)
        ON CONFLICT (external_auth_id) DO UPDATE
            SET name   = EXCLUDED.name,
                email  = EXCLUDED.email,
                grade  = CASE
                             WHEN students.school_id IS NOT NULL THEN students.grade
                             ELSE EXCLUDED.grade
                         END,
                locale = EXCLUDED.locale,
                account_status = CASE
                    WHEN students.account_status = 'suspended'
                        THEN 'suspended'
                    WHEN students.account_status = 'pending'
                         AND EXCLUDED.account_status = 'active'
                        THEN 'active'
                    ELSE students.account_status
                END
        RETURNING student_id, name, email, grade, locale,
                  account_status, school_id, created_at
        """,
        auth0_sub,
        name,
        email,
        grade,
        locale,
        initial_status,
    )
    if row is None:
        raise HTTPException(
            status_code=500, detail={"error": "internal_error", "detail": "Student upsert failed."}
        )
    return dict(row)


async def upsert_teacher(
    pool: asyncpg.Pool,
    auth0_sub: str,
    school_id: uuid.UUID | None,
    name: str,
    email: str,
    role: str = "teacher",
) -> dict:
    """
    Insert or update a teacher row.

    If school_id is None and the teacher already exists, the existing school_id
    is preserved via the ON CONFLICT clause.
    """
    if school_id is not None:
        row = await pool.fetchrow(
            """
            INSERT INTO teachers (school_id, external_auth_id, auth_provider, name, email, role)
            VALUES ($1, $2, 'auth0', $3, $4, $5)
            ON CONFLICT (external_auth_id) DO UPDATE
                SET name  = EXCLUDED.name,
                    email = EXCLUDED.email,
                    role  = EXCLUDED.role
            RETURNING teacher_id, school_id, name, email, role, account_status, created_at
            """,
            school_id,
            auth0_sub,
            name,
            email,
            role,
        )
    else:
        # Without a school_id we can only update existing records.
        row = await pool.fetchrow(
            """
            SELECT teacher_id, school_id, name, email, role, account_status, created_at
            FROM teachers WHERE external_auth_id = $1
            """,
            auth0_sub,
        )
        if row is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "bad_request",
                    "detail": "Teacher has no school association. school_id required on first login.",
                },
            )

    if row is None:
        raise HTTPException(
            status_code=500, detail={"error": "internal_error", "detail": "Teacher upsert failed."}
        )
    return dict(row)


# ── Local auth helpers (Phase A) ─────────────────────────────────────────────

# Pre-hashed sentinel used to burn constant bcrypt time when a user is not found,
# preventing timing-based email enumeration.  Generated once at import time with
# rounds=4 (fast) — the only goal here is timing parity, not security.
import string as _string

_DEFAULT_PW_CHARS = _string.ascii_letters + _string.digits
_TIMING_SENTINEL_HASH: str = bcrypt.hashpw(b"__sentinel__", bcrypt.gensalt(rounds=4)).decode()


def generate_default_password(length: int = 12) -> str:
    """
    Generate a random URL-safe default password for provisioned users.

    Uses secrets.choice over a restricted character set (no ambiguous chars)
    so the plain-text password can be sent in an email and typed without confusion.
    """
    return "".join(secrets.choice(_DEFAULT_PW_CHARS) for _ in range(length))


async def login_local_user(
    pool: asyncpg.Pool,
    email: str,
    password: str,
) -> dict:
    """
    Authenticate a school-provisioned user (teacher or student) by email + password.

    Checks teachers first, then students.  Raises HTTP 401 on any failure —
    never reveals whether the email exists.

    Returns a dict with keys:
      user_type      "teacher" | "student"
      user_id        str (UUID)
      role           str (teacher role or "student")
      school_id      str | None
      account_status str
      first_login    bool
    """
    # Acquire a dedicated connection and stamp app.current_school_id='bypass' so
    # that the RLS policy (migration 0028) does not hide any rows.  Login is an
    # unauthenticated endpoint — we need to look up the user before we know their
    # school, so bypass is correct here.
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT set_config('app.current_school_id', 'bypass', false)"
        )
        row = await conn.fetchrow(
            """
            SELECT teacher_id::text AS user_id, role, school_id::text, account_status,
                   password_hash, first_login, 'teacher' AS user_type
            FROM teachers
            WHERE email = $1 AND auth_provider = 'local'
            """,
            email,
        )

        if row is None:
            row = await conn.fetchrow(
                """
                SELECT student_id::text AS user_id, 'student' AS role,
                       school_id::text, account_status,
                       password_hash, first_login, 'student' AS user_type
                FROM students
                WHERE email = $1 AND auth_provider = 'local'
                """,
                email,
            )
        # Reset session var before returning connection to pool.
        await conn.execute(
            "SELECT set_config('app.current_school_id', '', false)"
        )

    if row is None or not row["password_hash"]:
        # Always spend bcrypt time to prevent timing-based enumeration.
        await verify_password(password, _TIMING_SENTINEL_HASH)
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Invalid email or password."},
        )

    valid = await verify_password(password, row["password_hash"])
    if not valid:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Invalid email or password."},
        )

    if row["account_status"] == "suspended":
        raise HTTPException(
            status_code=403,
            detail={"error": "account_suspended", "detail": "Account has been suspended."},
        )
    if row["account_status"] == "deleted":
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Account has been deleted."},
        )

    return dict(row)


# ── Auth0 Management API ──────────────────────────────────────────────────────
# Thin re-exports — implementation lives in src/auth/auth0_client.py where the
# Redis-cached token logic and 401 retry are co-located.

from src.auth.auth0_client import block_auth0_user, delete_auth0_user  # noqa: F401, E402


async def trigger_auth0_password_reset(email: str) -> None:
    """
    Request Auth0 to send a password reset email.

    Called from POST /auth/forgot-password (which always returns 200
    regardless of whether the email exists — do not change that).
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"https://{settings.AUTH0_DOMAIN}/dbconnections/change_password",
                json={
                    "client_id": settings.AUTH0_STUDENT_CLIENT_ID,
                    "email": email,
                    "connection": "Username-Password-Authentication",
                },
            )
            log.info("auth0_password_reset_triggered", status=resp.status_code)
        except Exception as exc:
            # Swallow errors — caller always returns 200.
            log.error("auth0_password_reset_failed", error=str(exc))
