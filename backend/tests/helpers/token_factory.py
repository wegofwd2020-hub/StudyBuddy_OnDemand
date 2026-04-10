"""
backend/tests/helpers/token_factory.py

Generate valid test JWTs for use in tests.

All tokens are signed with the test secrets defined in .env.test / conftest.py.
These tokens should never be used outside of tests.

Default IDs use deterministic fixed UUIDs (Rule 9 — no uuid4() in fixtures).
The d-prefix block (d1…d9) is reserved for token_factory defaults.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt

# Test secrets — match the values in .env.test / conftest overrides.
TEST_JWT_SECRET = "test-secret-do-not-use-in-production-aaaa"
TEST_ADMIN_JWT_SECRET = "test-admin-secret-do-not-use-in-prod-bbb"
JWT_ALGORITHM = "HS256"

# ── Deterministic default IDs (never uuid.uuid4() in fixtures) ───────────────
# Each role gets its own fixed UUID so default tokens are always reproducible.
_DEFAULT_STUDENT_ID      = "d1000000-0000-0000-0000-000000000001"
_DEFAULT_TEACHER_ID      = "d2000000-0000-0000-0000-000000000001"
_DEFAULT_SCHOOL_ID       = "d3000000-0000-0000-0000-000000000001"
_DEFAULT_ADMIN_ID        = "d4000000-0000-0000-0000-000000000001"
_DEFAULT_DEMO_STUDENT_ID = "d5000000-0000-0000-0000-000000000001"
_DEFAULT_DEMO_ACCOUNT_ID = "d6000000-0000-0000-0000-000000000001"
_DEFAULT_DEMO_TEACHER_ID = "d7000000-0000-0000-0000-000000000001"
_DEFAULT_DEMO_T_ACCT_ID  = "d8000000-0000-0000-0000-000000000001"


def make_student_token(
    student_id: str | None = None,
    grade: int = 8,
    locale: str = "en",
    account_status: str = "active",
    expire_minutes: int = 15,
) -> str:
    """Return a signed student JWT for testing."""
    sid = student_id or _DEFAULT_STUDENT_ID
    now = datetime.now(tz=UTC)
    payload = {
        "student_id": sid,
        "grade": grade,
        "locale": locale,
        "role": "student",
        "account_status": account_status,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        # jti is a JWT nonce — random is intentional; tests never assert on it.
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


_UNSET = object()  # sentinel for "use default"


def make_teacher_token(
    teacher_id: str | None = None,
    school_id: object = _UNSET,   # pass None explicitly for independent teachers
    role: str = "teacher",
    account_status: str = "active",
    expire_minutes: int = 15,
) -> str:
    """Return a signed teacher JWT for testing.

    Pass school_id=None explicitly to produce an independent-teacher token
    (school_id omitted from payload, matching the auth0 exchange path for
    teachers without a school affiliation).

    Omitting school_id (or passing the _UNSET sentinel) uses _DEFAULT_SCHOOL_ID.
    """
    tid = teacher_id or _DEFAULT_TEACHER_ID
    sid = _DEFAULT_SCHOOL_ID if school_id is _UNSET else school_id
    now = datetime.now(tz=UTC)
    payload = {
        "teacher_id": tid,
        "role": role,
        "account_status": account_status,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    # Only include school_id in the JWT when set — mirrors the real exchange endpoint.
    if sid is not None:
        payload["school_id"] = sid
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_admin_token(
    admin_id: str | None = None,
    role: str = "super_admin",
    expire_minutes: int = 60,
) -> str:
    """Return a signed admin JWT for testing."""
    aid = admin_id or _DEFAULT_ADMIN_ID
    now = datetime.now(tz=UTC)
    payload = {
        "admin_id": aid,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_ADMIN_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_demo_student_token(
    student_id: str | None = None,
    demo_account_id: str | None = None,
    expire_minutes: int = 15,
) -> str:
    """Return a signed demo_student JWT for testing."""
    sid = student_id or _DEFAULT_DEMO_STUDENT_ID
    did = demo_account_id or _DEFAULT_DEMO_ACCOUNT_ID
    now = datetime.now(tz=UTC)
    payload = {
        "student_id": sid,
        "grade": 8,
        "locale": "en",
        "role": "demo_student",
        "account_status": "active",
        "demo_account_id": did,
        "demo_expires_at": (now + timedelta(hours=24)).isoformat(),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_expired_student_token() -> str:
    """Return an already-expired student JWT."""
    return make_student_token(expire_minutes=-5)


def make_demo_teacher_token(
    teacher_id: str | None = None,
    demo_account_id: str | None = None,
    expire_minutes: int = 15,
) -> str:
    """Return a signed demo_teacher JWT for testing (role=demo_teacher, signed with JWT_SECRET)."""
    tid = teacher_id or _DEFAULT_DEMO_TEACHER_ID
    did = demo_account_id or _DEFAULT_DEMO_T_ACCT_ID
    now = datetime.now(tz=UTC)
    payload = {
        "teacher_id": tid,
        "school_id": None,
        "role": "demo_teacher",
        "account_status": "active",
        "demo_account_id": did,
        "demo_expires_at": (now + timedelta(hours=24)).isoformat(),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)
