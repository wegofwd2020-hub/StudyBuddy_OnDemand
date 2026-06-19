"""
tests/test_settings_locale.py

Tests for PATCH /auth/settings locale propagation (#470).

When a student changes their language the endpoint must re-mint the student
JWT carrying the new locale — content endpoints read the locale authoritatively
from the token, so without a fresh token the new language only takes effect
after the next login. A non-locale change must NOT return a token.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from jose import jwt

from tests.helpers.token_factory import JWT_ALGORITHM, TEST_JWT_SECRET, make_student_token


@pytest.mark.asyncio
async def test_locale_change_returns_reminted_token(client: AsyncClient, fake_redis):
    student_id = str(uuid.uuid4())
    token = make_student_token(student_id=student_id, grade=8, locale="en")

    response = await client.patch(
        "/api/v1/auth/settings",
        json={"locale": "es"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    new_token = response.json().get("token")
    assert new_token, "expected a re-minted token on locale change"

    decoded = jwt.decode(new_token, TEST_JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert decoded["locale"] == "es"
    assert decoded["student_id"] == student_id
    assert decoded["role"] == "student"


@pytest.mark.asyncio
async def test_non_locale_change_returns_no_token(client: AsyncClient, fake_redis):
    student_id = str(uuid.uuid4())
    token = make_student_token(student_id=student_id, grade=8, locale="en")

    response = await client.patch(
        "/api/v1/auth/settings",
        json={"display_name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json().get("token") is None


@pytest.mark.asyncio
async def test_invalid_locale_ignored_no_token(client: AsyncClient, fake_redis):
    student_id = str(uuid.uuid4())
    token = make_student_token(student_id=student_id, grade=8, locale="en")

    response = await client.patch(
        "/api/v1/auth/settings",
        json={"locale": "de"},  # unsupported — must be rejected, no re-mint
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json().get("token") is None
