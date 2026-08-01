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

from quiz_suite import constants as C


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


# Login is IP-rate-limited (AUTH_RATE_LIMIT=10 per AUTH_RATE_WINDOW=60s,
# backend/config.py). token_a/token_b are function-scoped fixtures, so
# without caching, every test that touches auth_a/auth_b performs a fresh
# POST /auth/login — across test_fixture.py + test_journey.py alone that's
# well past 10 logins inside one 60s window, and the suite intermittently
# 429s. Cache the token per-email at module scope instead: one real login per
# student per pytest process, every subsequent fixture use just returns the
# cached JWT. This assumes the token outlives the run — student JWTs are
# short-lived, but this suite finishes in well under 90 seconds, so a token
# cached for the process's lifetime never goes stale in practice. If the
# suite grows past that window, or a future test needs to exercise login
# behaviour itself (expiry, wrong password, etc.), give it its own uncached
# call to the real `/auth/login` endpoint rather than clearing this cache —
# clearing it would silently change what every other cached-token test is
# asserting against.
_token_cache: dict[str, str] = {}


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Return a student JWT, cached per-email for the life of the pytest process.

    The login response field is `token`, not `access_token`.
    """
    if email in _token_cache:
        return _token_cache[email]
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body["access_token"]
    _token_cache[email] = token
    return token


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
