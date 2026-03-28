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


async def verify_auth0_token(id_token: str) -> dict:
    """
    Verify an Auth0 id_token against the tenant JWKS.

    Returns decoded JWT claims on success.
    Raises HTTP 401 on any verification failure.
    """
    try:
        # Decode header to extract kid without verification.
        unverified_header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        log.warning("auth0_token_header_invalid", error=str(exc))
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "detail": "JWT header could not be parsed.",
            },
        )

    kid = unverified_header.get("kid")
    jwks = await _fetch_jwks()

    # Find matching key in JWKS.
    rsa_key: dict = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        # Key not found — JWKS may be stale; evict cache and retry once.
        log.warning("jwks_key_not_found", kid=kid, retrying=True)
        jwks_cache.pop(settings.AUTH0_JWKS_URL, None)
        jwks = await _fetch_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

    if not rsa_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "detail": "JWT signing key not found.",
            },
        )

    try:
        payload = jwt.decode(
            id_token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_STUDENT_CLIENT_ID,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Token has expired."},
        )
    except JWTError as exc:
        log.warning("auth0_token_verification_failed", error=str(exc))
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "detail": "JWT signature verification failed.",
            },
        )

    return payload


async def verify_auth0_teacher_token(id_token: str) -> dict:
    """Same as verify_auth0_token but uses AUTH0_TEACHER_CLIENT_ID as audience."""
    try:
        unverified_header = jwt.get_unverified_header(id_token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT header could not be parsed."},
        )

    kid = unverified_header.get("kid")
    jwks = await _fetch_jwks()

    rsa_key: dict = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {k: key[k] for k in ("kty", "kid", "n", "e")}
            break

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
            audience=settings.AUTH0_TEACHER_CLIENT_ID,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "detail": "Token has expired."},
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "detail": "JWT signature verification failed."},
        )

    return payload


# ── Internal JWT helpers ──────────────────────────────────────────────────────

def create_internal_jwt(payload: dict, secret: str, expire_minutes: int) -> str:
    """
    Sign a payload as an HS256 JWT.

    Always adds exp, iat, jti claims (per PHASE1_SETUP.md section 10.3).
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
      - requires_parental_consent=True  → account_status stays 'pending' (DB default)
        until the parental_consents record is updated to 'granted'

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
                grade  = EXCLUDED.grade,
                locale = EXCLUDED.locale
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
        raise HTTPException(status_code=500, detail={"error": "internal_error", "detail": "Student upsert failed."})
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
        raise HTTPException(status_code=500, detail={"error": "internal_error", "detail": "Teacher upsert failed."})
    return dict(row)


# ── Auth0 Management API ──────────────────────────────────────────────────────

async def _get_mgmt_token() -> str:
    """Obtain a short-lived Auth0 Management API token via client_credentials."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://{settings.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.AUTH0_MGMT_CLIENT_ID,
                "client_secret": settings.AUTH0_MGMT_CLIENT_SECRET,
                "audience": settings.AUTH0_MGMT_API_URL + "/",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def block_auth0_user(auth0_sub: str, blocked: bool = True) -> None:
    """Block or unblock a user via Auth0 Management API."""
    token = await _get_mgmt_token()
    user_id = auth0_sub.replace("|", "%7C")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{settings.AUTH0_MGMT_API_URL}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"blocked": blocked},
        )
        if resp.status_code not in (200, 204):
            log.error(
                "auth0_block_failed",
                auth0_sub=auth0_sub,
                status=resp.status_code,
            )


async def delete_auth0_user(auth0_sub: str) -> None:
    """Delete a user from Auth0 (GDPR erasure)."""
    token = await _get_mgmt_token()
    user_id = auth0_sub.replace("|", "%7C")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{settings.AUTH0_MGMT_API_URL}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code not in (200, 204):
            log.error(
                "auth0_delete_failed",
                auth0_sub=auth0_sub,
                status=resp.status_code,
            )


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
