"""
mobile/src/api/auth_client.py

Async HTTP client for the auth exchange endpoints.

The mobile app uses Auth0 PKCE to obtain an id_token, then exchanges it
for an internal JWT via the backend.  This module handles that exchange.

Layer rule: api layer only — no UI, no Kivy, no business logic.
"""

from __future__ import annotations

import os

import httpx

try:
    from mobile.config import BACKEND_URL  # type: ignore
except ImportError:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


async def exchange_id_token(id_token: str) -> dict:
    """
    Exchange an Auth0 id_token for an internal student JWT.

    POST /api/v1/auth/exchange → {token, refresh_token}

    Raises httpx.HTTPStatusError on non-2xx responses.
    The caller must inspect status_code for 403 (suspended / COPPA pending).
    """
    url = f"{BACKEND_URL}/api/v1/auth/exchange"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={"id_token": id_token})
        resp.raise_for_status()
        return resp.json()


async def get_auth0_signup_url() -> str:
    """
    Return the Auth0 Universal Login URL for new account creation.

    In practice this is the same authorize URL with prompt=signup added.
    Built client-side from config to avoid a network round-trip.
    """
    try:
        from mobile.config import AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_REDIRECT_URI  # type: ignore
        import urllib.parse
        params = {
            "response_type": "code",
            "client_id": AUTH0_CLIENT_ID,
            "redirect_uri": AUTH0_REDIRECT_URI,
            "scope": "openid profile email",
            "screen_hint": "signup",
        }
        return f"https://{AUTH0_DOMAIN}/authorize?" + urllib.parse.urlencode(params)
    except ImportError:
        return ""


async def get_auth0_reset_url(email: str = "") -> str:
    """Return the Auth0 password reset URL (opened in browser)."""
    try:
        from mobile.config import AUTH0_DOMAIN, AUTH0_CLIENT_ID  # type: ignore
        import urllib.parse
        params = {"client_id": AUTH0_CLIENT_ID}
        if email:
            params["email"] = email
        return f"https://{AUTH0_DOMAIN}/dbconnections/change_password?" + urllib.parse.urlencode(params)
    except ImportError:
        return ""
