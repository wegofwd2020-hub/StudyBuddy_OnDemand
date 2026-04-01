"""
tests/test_private_teacher.py

Tests for Issue #57 — multi-tier subscription model (private teacher tier).

Coverage:
  1.  test_register_private_teacher
  2.  test_register_duplicate_email
  3.  test_login_private_teacher
  4.  test_login_wrong_password
  5.  test_login_unknown_email
  6.  test_get_profile
  7.  test_profile_requires_auth
  8.  test_get_subscription_no_sub
  9.  test_list_available_teachers_empty
  10. test_admin_list_private_teachers
  11. test_admin_private_teachers_requires_permission
  12. test_curriculum_resolver_uses_teacher_path
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers.token_factory import (
    make_admin_token,
    make_private_teacher_token,
    make_student_token,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _admin_headers(role: str = "product_admin") -> dict:
    return {"Authorization": f"Bearer {make_admin_token(role=role)}"}


def _pt_headers(teacher_id: str) -> dict:
    return {"Authorization": f"Bearer {make_private_teacher_token(teacher_id=teacher_id)}"}


def _student_headers(student_id: str | None = None, grade: int = 8) -> dict:
    return {"Authorization": f"Bearer {make_student_token(student_id=student_id, grade=grade)}"}


async def _insert_private_teacher(
    db_conn,
    email: str = "teacher@example.com",
    name: str = "Test Teacher",
    password_hash: str = "$2b$12$fakehashfortest000000000000000000000000000000000",
) -> str:
    """Insert a private_teacher row directly and return teacher_id as str."""
    row = await db_conn.fetchrow(
        """
        INSERT INTO private_teachers (email, name, password_hash)
        VALUES ($1, $2, $3)
        RETURNING teacher_id::text
        """,
        email,
        name,
        password_hash,
    )
    return row["teacher_id"]


# ── 1. Register ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_private_teacher(client: AsyncClient):
    """POST /auth/private-teacher/register → 201 with token + teacher_id."""
    r = await client.post(
        "/api/v1/auth/private-teacher/register",
        json={
            "email": "newteacher@example.com",
            "name": "Alice Smith",
            "password": "SecurePass123!",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "token" in data
    assert "teacher_id" in data


# ── 2. Duplicate email → 409 ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering with the same email twice → 409 Conflict."""
    payload = {
        "email": "dup_teacher@example.com",
        "name": "Dup Teacher",
        "password": "SecurePass123!",
    }
    r1 = await client.post("/api/v1/auth/private-teacher/register", json=payload)
    assert r1.status_code == 201, r1.text

    r2 = await client.post("/api/v1/auth/private-teacher/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"] == "conflict"


# ── 3. Login ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_private_teacher(client: AsyncClient):
    """Register then login → 200 with token."""
    email = "login_teacher@example.com"
    password = "MyTestPass99!"

    reg = await client.post(
        "/api/v1/auth/private-teacher/register",
        json={"email": email, "name": "Login Teacher", "password": password},
    )
    assert reg.status_code == 201, reg.text

    r = await client.post(
        "/api/v1/auth/private-teacher/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data
    assert "teacher_id" in data


# ── 4. Wrong password → 401 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password → 401."""
    email = "wrongpass@example.com"
    await client.post(
        "/api/v1/auth/private-teacher/register",
        json={"email": email, "name": "WP Teacher", "password": "CorrectPass1!"},
    )

    r = await client.post(
        "/api/v1/auth/private-teacher/login",
        json={"email": email, "password": "WrongPass1!"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


# ── 5. Unknown email → 401 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """Login with unknown email → 401."""
    r = await client.post(
        "/api/v1/auth/private-teacher/login",
        json={"email": "nobody@example.com", "password": "Whatever1!"},
    )
    assert r.status_code == 401


# ── 6. GET /private-teacher/me ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    """Register then GET /private-teacher/me → 200 with email and name."""
    reg = await client.post(
        "/api/v1/auth/private-teacher/register",
        json={
            "email": "profile_teacher@example.com",
            "name": "Profile Teacher",
            "password": "TestPass123!",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["token"]
    teacher_id = reg.json()["teacher_id"]

    r = await client.get(
        "/api/v1/private-teacher/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "profile_teacher@example.com"
    assert data["name"] == "Profile Teacher"
    assert data["teacher_id"] == teacher_id


# ── 7. GET /private-teacher/me — no auth ─────────────────────────────────────


@pytest.mark.asyncio
async def test_profile_requires_auth(client: AsyncClient):
    """GET /private-teacher/me without token → 403 (forbidden role) or 401."""
    r = await client.get("/api/v1/private-teacher/me")
    assert r.status_code in (401, 403)


# ── 8. GET /private-teacher/subscription — no subscription ───────────────────


@pytest.mark.asyncio
async def test_get_subscription_no_sub(client: AsyncClient):
    """GET /private-teacher/subscription when no sub exists → plan=null."""
    reg = await client.post(
        "/api/v1/auth/private-teacher/register",
        json={
            "email": "nosub_teacher@example.com",
            "name": "NoSub Teacher",
            "password": "TestPass123!",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["token"]

    r = await client.get(
        "/api/v1/private-teacher/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] is None
    assert data["status"] is None
    assert data["pipeline_quota_monthly"] == 0
    assert data["max_students"] == 0


# ── 9. GET /subscription/teacher-access — empty list ─────────────────────────


@pytest.mark.asyncio
async def test_list_available_teachers_empty(client: AsyncClient):
    """GET /subscription/teacher-access → {teachers: []} when no active subs."""
    student_id = str(uuid.uuid4())
    r = await client.get(
        "/api/v1/subscription/teacher-access",
        headers=_student_headers(student_id),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "teachers" in data
    assert isinstance(data["teachers"], list)


# ── 10. Admin list private teachers ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_private_teachers(client: AsyncClient):
    """GET /admin/private-teachers → {teachers: [...], total ≥ 1}."""
    reg = await client.post(
        "/api/v1/auth/private-teacher/register",
        json={
            "email": "admin_list_teacher@example.com",
            "name": "Admin List Teacher",
            "password": "TestPass123!",
        },
    )
    assert reg.status_code == 201, reg.text

    r = await client.get(
        "/api/v1/admin/private-teachers",
        headers=_admin_headers("product_admin"),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "teachers" in data
    assert "total" in data
    assert data["total"] >= 1
    emails = [t["email"] for t in data["teachers"]]
    assert "admin_list_teacher@example.com" in emails


# ── 11. Admin endpoint requires permission ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_private_teachers_requires_permission(client: AsyncClient):
    """GET /admin/private-teachers with student token → 403."""
    r = await client.get(
        "/api/v1/admin/private-teachers",
        headers=_student_headers(),
    )
    assert r.status_code in (401, 403)


# ── 12. Curriculum resolver — teacher path ────────────────────────────────────


@pytest.mark.asyncio
async def test_curriculum_resolver_uses_teacher_path(client: AsyncClient):
    """
    Resolver returns teacher curriculum_id when student has active teacher access
    and no school affiliation.

    Uses the shared app pool directly so inserts are visible to the resolver.
    """
    import datetime as _dt
    from src.curriculum.resolver import _resolve_from_db

    from main import app as _app

    pool = _app.state.pool

    teacher_id = uuid.uuid4()
    student_id = uuid.uuid4()
    current_year = _dt.datetime.now(_dt.UTC).year
    curriculum_id = f"teacher-resolver-{teacher_id}-g8"

    async with pool.acquire() as conn:
        # Create a private teacher
        await conn.execute(
            """
            INSERT INTO private_teachers (teacher_id, email, name, password_hash)
            VALUES ($1, $2, $3, $4)
            """,
            teacher_id,
            f"resolver_teacher_{teacher_id}@example.com",
            "Resolver Teacher",
            "$2b$12$fakehashfortest000000000000000000000000000000000",
        )

        # Give teacher an active subscription
        await conn.execute(
            """
            INSERT INTO teacher_subscriptions
                (teacher_id, plan, status, pipeline_quota_monthly, pipeline_resets_at)
            VALUES ($1, 'basic', 'active', 2, NOW() + INTERVAL '1 month')
            """,
            teacher_id,
        )

        # Insert a curriculum owned by the teacher (name column required)
        await conn.execute(
            """
            INSERT INTO curricula
                (curriculum_id, name, school_id, grade, year, status,
                 restrict_access, owner_type, owner_id, activated_at)
            VALUES ($1, $2, NULL, $3, $4, 'active', false, 'teacher', $5, NOW())
            """,
            curriculum_id,
            "Teacher Grade 8 Curriculum",
            8,
            current_year,
            teacher_id,
        )

        # Create a student
        await conn.execute(
            """
            INSERT INTO students
                (student_id, external_auth_id, auth_provider, name, email,
                 grade, locale, account_status)
            VALUES ($1, $2, 'auth0', 'Resolver Student', $3, 8, 'en', 'active')
            """,
            student_id,
            f"auth0|resolver-{student_id}",
            f"resolver_student_{student_id}@example.com",
        )

        # Link student → teacher with active access
        await conn.execute(
            """
            INSERT INTO student_teacher_access
                (student_id, teacher_id, status)
            VALUES ($1, $2, 'active')
            """,
            student_id,
            teacher_id,
        )

    try:
        resolved = await _resolve_from_db(pool, str(student_id), 8, None)
        assert resolved == curriculum_id, (
            f"Expected teacher curriculum {curriculum_id!r}, got {resolved!r}"
        )
    finally:
        # Clean up (pool doesn't auto-rollback unlike db_conn fixture)
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM student_teacher_access WHERE student_id = $1", student_id
            )
            await conn.execute(
                "DELETE FROM students WHERE student_id = $1", student_id
            )
            await conn.execute(
                "DELETE FROM curricula WHERE curriculum_id = $1", curriculum_id
            )
            await conn.execute(
                "DELETE FROM teacher_subscriptions WHERE teacher_id = $1", teacher_id
            )
            await conn.execute(
                "DELETE FROM private_teachers WHERE teacher_id = $1", teacher_id
            )
