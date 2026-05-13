"""
backend/src/demo/test_run_router.py

Demo "test run" — one form, two accounts.

A single submission at the marketing site ("Try a test run") provisions BOTH a
demo teacher AND a demo student account so the visitor can experience both
personas using the same /signin URL. One verification email goes out, one
credentials email comes back with both sets of login details.

Routes (all prefixed /api/v1 in app_factory.py):
  POST /demo/test-run/request          — submit name+email → receive verification link
  GET  /demo/test-run/verify/{token}   — verify both, create both accounts,
                                          send combined credentials email

Implementation notes:
  - The student account uses `{local}+student@{domain}` as its login email; the
    teacher uses `{local}+teacher@{domain}`. Both rows reference the visitor's
    real email in the demo_requests / demo_teacher_requests metadata. This
    sidesteps the UNIQUE constraint on students.email / teachers.email AND
    keeps universal-login simple (each role probes a distinct email).
  - The same verification token string is written into BOTH demo_verifications
    AND demo_teacher_verifications (UNIQUE is per-table, so no collision). One
    token in the URL covers both records.
  - Name and the original email are cached in Redis between request and verify
    so the credentials email can address the visitor by name and arrive at the
    right inbox. Redis TTL matches DEMO_VERIFICATION_TOKEN_TTL_MINUTES.
  - Rate limited via the existing demo_req:{ip} bucket (3/IP/hour) — a test-run
    request counts the same as a single demo request, since both create accounts.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime

from config import settings
from fastapi import APIRouter, HTTPException, Request

from src.auth.service import hash_password
from src.auth.tasks import (
    send_test_run_credentials_email_task,
    send_test_run_verification_email_task,
)
from src.core.db import get_db
from src.core.redis_client import get_redis
from src.demo.schemas import DemoTestRunRequestInput
from src.demo.service import (
    _generate_demo_password,
    count_active_demos,
    create_demo_request,
    create_demo_student_and_account,
    get_active_demo_account_by_email,
    get_pending_verification_by_email,
    get_verification_by_token,
    mark_request_verified,
    mark_verification_used,
)
from src.demo.teacher_service import (
    _generate_demo_teacher_password,
    count_active_demo_teachers,
    create_demo_teacher_and_account,
    create_demo_teacher_request,
    get_active_demo_teacher_account_by_email,
    get_pending_teacher_verification_by_email,
    get_teacher_verification_by_token,
    mark_teacher_request_verified,
    mark_teacher_verification_used,
)
from src.utils.logger import get_logger

log = get_logger("demo.test_run")
router = APIRouter(tags=["demo-test-run"])

# Shared rate-limit bucket with the standalone /demo/request endpoint — keep the
# same prefix so an attacker can't combine the two to double their budget.
_REQ_RATE_PREFIX = "demo_req:"
_REQ_RATE_LIMIT = 3
_REQ_RATE_WINDOW = 3600  # 1 hour

# Cache name + original_email between request and verify, keyed by verification
# token. TTL slightly longer than the verification token so the email can still
# be addressed by name if the verify call arrives near expiry.
_META_REDIS_PREFIX = "demo_testrun_meta:"


def _split_plus(email: str) -> tuple[str, str]:
    """Return (local-part, domain) of an email address."""
    local, _, domain = email.partition("@")
    return local, domain


def _synthesise_email(original: str, suffix: str) -> str:
    """Build `{local}+{suffix}@{domain}` for the per-role demo accounts."""
    local, domain = _split_plus(original)
    # Strip any existing +tag so we don't end up with foo+student+teacher@…
    local = local.split("+", 1)[0]
    return f"{local}+{suffix}@{domain}"


# ── POST /demo/test-run/request ──────────────────────────────────────────────


@router.post("/demo/test-run/request", status_code=200)
async def request_test_run(body: DemoTestRunRequestInput, request: Request):
    """
    Submit name + email to receive a verification link. Clicking the link
    provisions both a demo teacher and a demo student account and emails the
    combined credentials.
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)
    name = body.name
    original_email = str(body.email)

    # Pre-compute the synthetic per-role emails so we can guard against
    # duplicate active accounts before writing anything.
    student_email = _synthesise_email(original_email, "student")
    teacher_email = _synthesise_email(original_email, "teacher")

    # IP rate limit (shared with /demo/request — see module docstring)
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{_REQ_RATE_PREFIX}{client_ip}"
    count_raw = await redis.get(rate_key)
    count = int(count_raw) if count_raw else 0
    if count >= _REQ_RATE_LIMIT:
        log.warning("test_run_request_rate_limited", ip=client_ip, email=original_email)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": "Too many demo requests. Please try again in an hour.",
                "correlation_id": cid,
            },
        )

    async with get_db(request) as conn:
        # Block if either role is already active for this visitor.
        if await get_active_demo_account_by_email(conn, student_email):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "demo_already_active",
                    "detail": "A test-run for this email is already active. Please check your inbox.",
                    "correlation_id": cid,
                },
            )
        if await get_active_demo_teacher_account_by_email(conn, teacher_email):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "demo_already_active",
                    "detail": "A test-run for this email is already active. Please check your inbox.",
                    "correlation_id": cid,
                },
            )

        # Block if a verification is already pending for either role.
        if await get_pending_verification_by_email(conn, student_email):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "verification_pending",
                    "detail": "A verification email was already sent. Please check your inbox.",
                    "correlation_id": cid,
                },
            )
        if await get_pending_teacher_verification_by_email(conn, teacher_email):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "verification_pending",
                    "detail": "A verification email was already sent. Please check your inbox.",
                    "correlation_id": cid,
                },
            )

        user_agent = request.headers.get("user-agent")

        # Create student request + teacher request in one transaction. Generate
        # one token string and write it into both verification tables.
        token = secrets.token_urlsafe(32)
        ttl = settings.DEMO_VERIFICATION_TOKEN_TTL_MINUTES
        from datetime import timedelta

        expires_at = datetime.now(UTC) + timedelta(minutes=ttl)

        async with conn.transaction():
            student_request_id = await create_demo_request(
                conn, student_email, client_ip, user_agent
            )
            # Persist visitor name on the +student row so the super-admin
            # /admin/test-runs page can show who requested. (The +teacher row
            # mirrors the same identity; we only need to store name once.)
            await conn.execute(
                "UPDATE demo_requests SET name = $1 WHERE id = $2",
                name,
                student_request_id,
            )
            await conn.execute(
                """
                INSERT INTO demo_verifications (request_id, email, token, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                student_request_id,
                student_email,
                token,
                expires_at,
            )

            teacher_request_id = await create_demo_teacher_request(
                conn, teacher_email, client_ip, user_agent
            )
            await conn.execute(
                """
                INSERT INTO demo_teacher_verifications (request_id, email, token, expires_at)
                VALUES ($1, $2, $3, $4)
                """,
                teacher_request_id,
                teacher_email,
                token,
                expires_at,
            )

    # Increment shared rate-limit counter (after the DB commit so a failed
    # commit doesn't burn budget).
    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, _REQ_RATE_WINDOW)
    await pipe.execute()

    # Cache the visitor's display name + original email for the credentials
    # email. Slightly longer TTL than the verification window so the verify
    # handler still finds the name if the token is clicked near expiry.
    await redis.set(
        f"{_META_REDIS_PREFIX}{token}",
        json.dumps({"name": name, "original_email": original_email}),
        ex=(ttl + 30) * 60,
    )

    try:
        send_test_run_verification_email_task.delay(original_email, token)
    except Exception as exc:
        log.error(
            "test_run_verification_email_dispatch_failed",
            email=original_email,
            error=str(exc),
        )

    log.info("test_run_request_created", email=original_email, ip=client_ip)
    return {"message": "Verification email sent. Please check your inbox."}


# ── GET /demo/test-run/verify/{token} ────────────────────────────────────────


_TEST_RUN_LOCK_KEY = 1_953_719_637  # one off the existing demo lock key

# Identifiers for the seeded demo sandbox (see backend/scripts/seed_demo.py).
# A missing sandbox makes verify fall back to the standalone-demo defaults
# (no school, grade 8) so the test-run flow still completes in environments
# where seed_demo.py has not been run.
_DEMO_SCHOOL_CONTACT_EMAIL = "admin@milfordwaterford.edu"
_DEMO_TEST_RUN_GRADE = 11
_DEMO_TEST_RUN_STREAM = "science"
_DEMO_TEST_RUN_CURRICULUM_ID = "default-2026-g11-science"


async def _resolve_demo_school(conn):
    """Return the MilfordWaterford school_id, or None if the seed is absent."""
    school_row = await conn.fetchrow(
        "SELECT school_id FROM schools WHERE contact_email = $1",
        _DEMO_SCHOOL_CONTACT_EMAIL,
    )
    return school_row["school_id"] if school_row else None


@router.get("/demo/test-run/verify/{token}", status_code=200)
async def verify_test_run(token: str, request: Request):
    """
    Verify the test-run token: provisions both a demo teacher and a demo
    student account and emails the combined credentials to the visitor.
    """
    cid = getattr(request.state, "correlation_id", "")
    redis = get_redis(request)

    # Look up both verification rows under the same token string.
    async with get_db(request) as conn:
        student_row = await get_verification_by_token(conn, token)
        teacher_row = await get_teacher_verification_by_token(conn, token)

        if student_row is None or teacher_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "token_not_found",
                    "detail": "Verification token is invalid.",
                    "correlation_id": cid,
                },
            )

        # Either side already used / expired / verified → reject uniformly.
        for row in (student_row, teacher_row):
            if row["used_at"] is not None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "token_already_used",
                        "detail": "This verification link has already been used.",
                        "correlation_id": cid,
                    },
                )
            if row["expires_at"] < datetime.now(UTC):
                raise HTTPException(
                    status_code=410,
                    detail={
                        "error": "token_expired",
                        "detail": "This verification link has expired. Please request a new test run.",
                        "correlation_id": cid,
                    },
                )
            if row["request_status"] == "verified":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "already_verified",
                        "detail": "This test-run request has already been verified.",
                        "correlation_id": cid,
                    },
                )

        student_email = student_row["email"]
        teacher_email = teacher_row["email"]
        student_request_id = student_row["request_id"]
        teacher_request_id = teacher_row["request_id"]

        # Resolve the seeded demo school (MilfordWaterford). May be None if the
        # sandbox hasn't been seeded; in that case create_demo_*_and_account
        # falls back to no-school defaults and the per-visitor classroom is
        # skipped entirely.
        sandbox_school_id = await _resolve_demo_school(conn)

        # Pull the visitor's display name out of Redis up front so the rosters
        # ("Pat Tester" instead of "pat.tester+student") read sensibly when the
        # demo teacher opens their classroom view.
        meta_raw = await redis.get(f"{_META_REDIS_PREFIX}{token}")
        visitor_name = None
        inbox_email = student_email.replace("+student", "", 1)
        if meta_raw:
            try:
                meta = json.loads(meta_raw if isinstance(meta_raw, str) else meta_raw.decode())
                visitor_name = meta.get("name") or None
                inbox_email = meta.get("original_email") or inbox_email
            except (ValueError, TypeError):
                pass

        student_display = (
            f"{visitor_name} (test student)" if visitor_name else student_email.split("@")[0]
        )
        teacher_display = (
            f"{visitor_name} (test teacher)" if visitor_name else teacher_email.split("@")[0]
        )

        # Generate passwords + hashes BEFORE entering the transaction (bcrypt
        # is slow — keep the lock window narrow).
        student_plain = _generate_demo_password()
        teacher_plain = _generate_demo_teacher_password()
        student_hash = await hash_password(student_plain)
        teacher_hash = await hash_password(teacher_plain)

        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock($1)", _TEST_RUN_LOCK_KEY)

            # Combined capacity check — both pools must have a free slot.
            student_active = await count_active_demos(conn)
            teacher_active = await count_active_demo_teachers(conn)
            if (
                student_active >= settings.DEMO_MAX_ACTIVE
                or teacher_active >= settings.DEMO_TEACHER_MAX_ACTIVE
            ):
                log.warning(
                    "test_run_max_active_reached",
                    student_active=student_active,
                    teacher_active=teacher_active,
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "demo_capacity_reached",
                        "detail": "All demo slots are currently occupied. Please try again later.",
                        "correlation_id": cid,
                    },
                )

            student_account = await create_demo_student_and_account(
                conn,
                request_id=student_request_id,
                email=student_email,
                from_password=student_plain,
                password_hash=student_hash,
                school_id=sandbox_school_id,
                grade=_DEMO_TEST_RUN_GRADE if sandbox_school_id else 8,
                stream=_DEMO_TEST_RUN_STREAM if sandbox_school_id else None,
                student_name=student_display,
            )
            await mark_verification_used(conn, student_row["verif_id"])
            await mark_request_verified(conn, student_request_id)

            teacher_account = await create_demo_teacher_and_account(
                conn,
                request_id=teacher_request_id,
                email=teacher_email,
                password_hash=teacher_hash,
                school_id=sandbox_school_id,
                role="teacher",
                teacher_name=teacher_display,
            )
            await mark_teacher_verification_used(conn, teacher_row["verif_id"])
            await mark_teacher_request_verified(conn, teacher_request_id)

            # Create a per-visitor classroom owned by the demo teacher and
            # enroll the demo student in it. This way the visitor signs in
            # to the teacher portal and immediately sees a class they "own"
            # with their student in the roster — instead of an empty
            # dashboard or a shared seeded classroom. Skipped if the
            # sandbox school isn't seeded.
            if sandbox_school_id is not None:
                classroom_label = (
                    f"{visitor_name}'s Grade 11 Science"
                    if visitor_name
                    else "Demo · Grade 11 Science"
                )
                visitor_classroom_id = await conn.fetchval(
                    """
                    INSERT INTO classrooms (school_id, teacher_id, name, grade, status)
                    VALUES ($1, $2, $3, $4, 'active')
                    RETURNING classroom_id
                    """,
                    sandbox_school_id,
                    teacher_account["teacher_id"],
                    classroom_label,
                    _DEMO_TEST_RUN_GRADE,
                )
                # Attach the Grade 11 Science curriculum so the classroom has
                # content. Matches what the seeded Milford classrooms do.
                await conn.execute(
                    """
                    INSERT INTO classroom_packages (classroom_id, curriculum_id, sort_order)
                    VALUES ($1, $2, 0)
                    ON CONFLICT DO NOTHING
                    """,
                    visitor_classroom_id,
                    _DEMO_TEST_RUN_CURRICULUM_ID,
                )
                # Enroll the visitor's demo student so the roster isn't empty.
                await conn.execute(
                    """
                    INSERT INTO classroom_students (classroom_id, student_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    visitor_classroom_id,
                    student_account["student_id"],
                )

    # `visitor_name` and `inbox_email` were already resolved before the
    # transaction. Fall back to "there" if the visitor name expired from cache.
    name = visitor_name or "there"

    try:
        send_test_run_credentials_email_task.delay(
            inbox_email,
            name,
            teacher_email,
            teacher_plain,
            student_email,
            student_plain,
        )
    except Exception as exc:
        log.error(
            "test_run_credentials_email_dispatch_failed",
            email=inbox_email,
            error=str(exc),
        )

    # Clean up the metadata cache — the credentials email has already been
    # queued, and a re-click on the verify URL would now 409 (already_used).
    await redis.delete(f"{_META_REDIS_PREFIX}{token}")

    log.info("test_run_verified", email=inbox_email)
    return {
        "message": (
            "Test run ready. We've emailed you the teacher and student "
            "credentials — check your inbox."
        )
    }
