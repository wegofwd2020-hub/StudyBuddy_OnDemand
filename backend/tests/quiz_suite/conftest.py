"""
Fixtures for the live quiz suite.

Deliberately does NOT import the FastAPI app or reuse backend/tests/conftest.py:
that conftest builds an app bound to studybuddy_test, which is the opposite of
what this suite tests. Here we speak HTTP to the already-running app.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest
import pytest_asyncio

from tests.quiz_suite import constants as C


@pytest_asyncio.fixture
async def api():
    async with httpx.AsyncClient(base_url=C.API_BASE, timeout=20.0) as client:
        yield client


@pytest.fixture(scope="session")
def fixture_data() -> dict:
    """The handoff file written by seed.py. Fails loudly if the seed never ran."""
    if not os.path.exists(C.FIXTURE_PATH):
        pytest.fail(
            f"{C.FIXTURE_PATH} missing — run scripts/quiz_suite.sh, which seeds first."
        )
    with open(C.FIXTURE_PATH) as fh:
        return json.load(fh)


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Return a student JWT. The login response field is `token`, not `access_token`."""
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    return body.get("token") or body["access_token"]


@pytest_asyncio.fixture
async def token_a(api) -> str:
    return await login(api, C.STUDENT_A_EMAIL, C.STUDENT_PASSWORD)


@pytest_asyncio.fixture
async def token_b(api) -> str:
    return await login(api, C.STUDENT_B_EMAIL, C.STUDENT_PASSWORD)


@pytest.fixture
def auth_a(token_a) -> dict:
    return {"Authorization": f"Bearer {token_a}"}


@pytest.fixture
def auth_b(token_b) -> dict:
    return {"Authorization": f"Bearer {token_b}"}
