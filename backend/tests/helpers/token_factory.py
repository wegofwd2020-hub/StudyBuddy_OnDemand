"""
backend/tests/helpers/token_factory.py

Generate valid test JWTs for use in tests.

All tokens are signed with the test secrets defined in .env.test / conftest.py.
These tokens should never be used outside of tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

# Test secrets — match the values in .env.test / conftest overrides.
TEST_JWT_SECRET = "test-secret-do-not-use-in-production-aaaa"
TEST_ADMIN_JWT_SECRET = "test-admin-secret-do-not-use-in-prod-bbb"
JWT_ALGORITHM = "HS256"


def make_student_token(
    student_id: str | None = None,
    grade: int = 8,
    locale: str = "en",
    account_status: str = "active",
    expire_minutes: int = 15,
) -> str:
    """Return a signed student JWT for testing."""
    sid = student_id or str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    payload = {
        "student_id": sid,
        "grade": grade,
        "locale": locale,
        "role": "student",
        "account_status": account_status,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_teacher_token(
    teacher_id: str | None = None,
    school_id: str | None = None,
    role: str = "teacher",
    account_status: str = "active",
    expire_minutes: int = 15,
) -> str:
    """Return a signed teacher JWT for testing."""
    tid = teacher_id or str(uuid.uuid4())
    sid = school_id or str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    payload = {
        "teacher_id": tid,
        "school_id": sid,
        "role": role,
        "account_status": account_status,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_admin_token(
    admin_id: str | None = None,
    role: str = "super_admin",
    expire_minutes: int = 60,
) -> str:
    """Return a signed admin JWT for testing."""
    aid = admin_id or str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    payload = {
        "admin_id": aid,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TEST_ADMIN_JWT_SECRET, algorithm=JWT_ALGORITHM)


def make_expired_student_token() -> str:
    """Return an already-expired student JWT."""
    return make_student_token(expire_minutes=-5)
