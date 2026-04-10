"""
mobile/tests/test_login_screen_logic.py

Unit tests for LoginScreen pure logic (no Kivy, no network).

Tests cover:
  - Error message mapping for different HTTP status codes / exception types
  - PKCE verifier stored during flow start
  - Callback URL parsing (via auth0_client.extract_code_from_callback)
  - token_store save/load/delete roundtrip
  - State field initialisation
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mobile.src.ui.LoginScreen import LoginScreen, _map_error, _ERROR_MESSAGES  # noqa: E402
from mobile.src.auth.auth0_client import extract_code_from_callback  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def screen():
    return LoginScreen()


# ── Initial state ─────────────────────────────────────────────────────────────


def test_initial_state_is_default(screen):
    assert screen._state == "default"


def test_initial_pkce_verifier_empty(screen):
    assert screen._pkce_verifier == ""


# ── Error message mapping ─────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _FakeHTTPError(Exception):
    def __init__(self, status_code: int, body: dict | None = None):
        super().__init__(f"HTTP {status_code}")
        self.response = _FakeResponse(status_code, body)


def test_error_403_suspended_returns_suspended_message():
    exc = _FakeHTTPError(403, {"detail": "account suspended"})
    assert _map_error(exc) == _ERROR_MESSAGES["suspended"]


def test_error_403_coppa_returns_coppa_message():
    exc = _FakeHTTPError(403, {"detail": "coppa consent pending"})
    assert _map_error(exc) == _ERROR_MESSAGES["coppa_pending"]


def test_error_network_timeout_returns_network_message():
    exc = ConnectionError("network timeout")
    assert _map_error(exc) == _ERROR_MESSAGES["network"]


def test_error_generic_returns_server_message():
    exc = RuntimeError("unexpected internal state")
    assert _map_error(exc) == _ERROR_MESSAGES["server"]


def test_all_error_messages_are_age_appropriate():
    """No technical terms like 'HTTP', 'JWT', 'Auth0' in any error message."""
    technical_terms = ["http", "jwt", "auth0", "traceback", "exception", "stack"]
    for key, msg in _ERROR_MESSAGES.items():
        low = msg.lower()
        for term in technical_terms:
            assert term not in low, f"Error '{key}' contains technical term '{term}': {msg!r}"


# ── PKCE callback parsing ─────────────────────────────────────────────────────


def test_extract_code_from_valid_callback():
    url = "studybuddy://callback?code=abc123&state=xyz"
    code = extract_code_from_callback(url)
    assert code == "abc123"


def test_extract_code_returns_none_on_missing_code():
    url = "studybuddy://callback?state=xyz"
    code = extract_code_from_callback(url)
    assert code is None


def test_extract_code_returns_none_on_empty_url():
    code = extract_code_from_callback("")
    assert code is None


def test_extract_code_handles_long_code():
    long_code = uuid.uuid4().hex * 4
    url = f"studybuddy://callback?code={long_code}"
    code = extract_code_from_callback(url)
    assert code == long_code


def test_extract_code_handles_multiple_params():
    url = "studybuddy://callback?code=mycode&state=abc&session_state=def"
    code = extract_code_from_callback(url)
    assert code == "mycode"


# ── token_store roundtrip ─────────────────────────────────────────────────────


def test_token_save_and_load(tmp_path, monkeypatch):
    from mobile.src.auth import token_store

    monkeypatch.setattr(token_store, "_get_user_data_dir", lambda: str(tmp_path))

    token_store.save_token("test.token", "my-internal-jwt")
    loaded = token_store.load_token("test.token")
    assert loaded == "my-internal-jwt"


def test_token_load_returns_none_if_missing(tmp_path, monkeypatch):
    from mobile.src.auth import token_store

    monkeypatch.setattr(token_store, "_get_user_data_dir", lambda: str(tmp_path))

    result = token_store.load_token("nonexistent.token")
    assert result is None


def test_token_delete_removes_file(tmp_path, monkeypatch):
    from mobile.src.auth import token_store

    monkeypatch.setattr(token_store, "_get_user_data_dir", lambda: str(tmp_path))

    token_store.save_token("del.token", "value")
    assert token_store.token_exists("del.token")
    token_store.delete_token("del.token")
    assert not token_store.token_exists("del.token")


def test_token_delete_is_safe_when_missing(tmp_path, monkeypatch):
    from mobile.src.auth import token_store

    monkeypatch.setattr(token_store, "_get_user_data_dir", lambda: str(tmp_path))

    # Should not raise
    token_store.delete_token("ghost.token")


def test_token_exists_returns_false_for_empty_file(tmp_path, monkeypatch):
    from mobile.src.auth import token_store

    monkeypatch.setattr(token_store, "_get_user_data_dir", lambda: str(tmp_path))

    # Write an empty file
    path = tmp_path / "empty.token"
    path.write_text("")
    assert not token_store.token_exists("empty.token")


# ── PKCE pair generation ──────────────────────────────────────────────────────


def test_generate_pkce_pair_produces_different_values():
    from mobile.src.auth.auth0_client import generate_pkce_pair
    v1, c1 = generate_pkce_pair()
    v2, c2 = generate_pkce_pair()
    assert v1 != v2
    assert c1 != c2


def test_generate_pkce_verifier_is_url_safe():
    from mobile.src.auth.auth0_client import generate_pkce_pair
    import re
    verifier, _ = generate_pkce_pair()
    assert re.match(r"^[A-Za-z0-9\-_]+$", verifier), f"verifier not URL-safe: {verifier!r}"


def test_generate_pkce_challenge_is_url_safe():
    from mobile.src.auth.auth0_client import generate_pkce_pair
    import re
    _, challenge = generate_pkce_pair()
    assert re.match(r"^[A-Za-z0-9\-_]+$", challenge), f"challenge not URL-safe: {challenge!r}"
