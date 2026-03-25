"""
mobile/src/auth/auth0_client.py

Auth0 PKCE flow for the Kivy mobile app.

There is no official Auth0 SDK for Kivy/Python.
This module implements the Authorization Code + PKCE flow manually via httpx.

Flow:
  1. generate_pkce_pair()        — produce code_verifier + code_challenge
  2. get_auth0_login_url()       — build the authorize URL
  3. open_auth0_login()          — open in system browser
  4. extract_code_from_callback()— parse the deep link callback
  5. exchange_code_for_tokens()  — POST to Auth0 token endpoint
  6. (caller) POST /auth/exchange to backend with the id_token

Never stores secrets. Never calls the backend directly — that is the caller's
responsibility using the backend API client.
"""

from __future__ import annotations

import base64
import hashlib
import os
import urllib.parse
import webbrowser

import httpx
from kivy.utils import platform

import config as app_config


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate a PKCE code_verifier and code_challenge.

    Returns:
        (code_verifier, code_challenge)
        code_challenge is the SHA-256 base64url-encoded hash of code_verifier.
    """
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def get_auth0_login_url(code_challenge: str) -> str:
    """
    Build the Auth0 Universal Login authorization URL.

    Args:
        code_challenge: base64url-encoded SHA-256 hash of code_verifier

    Returns:
        Full authorization URL to open in the browser.
    """
    params = {
        "response_type": "code",
        "client_id": app_config.AUTH0_CLIENT_ID,
        "redirect_uri": app_config.AUTH0_REDIRECT_URI,
        "scope": "openid profile email",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"https://{app_config.AUTH0_DOMAIN}/authorize?" + urllib.parse.urlencode(params)


def open_auth0_login(url: str) -> None:
    """
    Open the Auth0 login URL in the system browser.

    On Android/iOS this triggers a custom tab or Safari view.
    On desktop it opens the default browser.
    """
    if platform in ("android", "ios"):
        webbrowser.open(url)
    else:
        webbrowser.open_new(url)


def extract_code_from_callback(callback_url: str) -> str | None:
    """
    Parse the authorization code from the deep-link callback URL.

    Args:
        callback_url: e.g. "studybuddy://callback?code=abc123&state=..."

    Returns:
        The authorization code string, or None if not present.
    """
    parsed = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(parsed.query)
    codes = params.get("code")
    return codes[0] if codes else None


async def exchange_code_for_tokens(code: str, code_verifier: str) -> dict:
    """
    Exchange an authorization code for Auth0 tokens.

    Calls the Auth0 /oauth/token endpoint via the PKCE flow.

    Args:
        code:          The authorization code from the callback URL.
        code_verifier: The original code_verifier string (not the challenge).

    Returns:
        Dict containing id_token, access_token, and (optionally) refresh_token.

    Raises:
        httpx.HTTPStatusError if Auth0 returns an error response.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://{app_config.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": app_config.AUTH0_CLIENT_ID,
                "code": code,
                "redirect_uri": app_config.AUTH0_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        return resp.json()
