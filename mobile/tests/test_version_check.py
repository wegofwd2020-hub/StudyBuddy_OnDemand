"""
mobile/tests/test_version_check.py

Unit tests for app version check logic in mobile/main.py.

Covers:
  - _version_tuple() parsing
  - _check_version_thread(): upgrade required when below minimum
  - _check_version_thread(): upgrade banner when below latest but >= minimum
  - _check_version_thread(): no UI calls when already at latest
  - _check_version_thread(): network failure is non-fatal (app continues)
  - X-App-Version header is sent on every API call (app_headers / version_headers)
  - APP_VERSION is read from config, not hardcoded
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the mobile package root is importable without Kivy installed.
# We stub out kivy before any mobile import so tests run in CI without
# a display server.
# ---------------------------------------------------------------------------

# Kivy top-level stub
kivy_stub = MagicMock()
kivy_stub.app = MagicMock()
kivy_stub.app.App = object  # base class — StudyBuddyApp won't be instantiated
kivy_stub.clock = MagicMock()
kivy_stub.clock.mainthread = lambda fn: fn  # no-op in tests
kivy_stub.uix = MagicMock()
kivy_stub.uix.boxlayout = MagicMock()
kivy_stub.uix.button = MagicMock()
kivy_stub.uix.label = MagicMock()
kivy_stub.uix.popup = MagicMock()
kivy_stub.uix.screenmanager = MagicMock()

sys.modules.setdefault("kivy", kivy_stub)
sys.modules.setdefault("kivy.app", kivy_stub.app)
sys.modules.setdefault("kivy.clock", kivy_stub.clock)
sys.modules.setdefault("kivy.uix", kivy_stub.uix)
sys.modules.setdefault("kivy.uix.boxlayout", kivy_stub.uix.boxlayout)
sys.modules.setdefault("kivy.uix.button", kivy_stub.uix.button)
sys.modules.setdefault("kivy.uix.label", kivy_stub.uix.label)
sys.modules.setdefault("kivy.uix.popup", kivy_stub.uix.popup)
sys.modules.setdefault("kivy.uix.screenmanager", kivy_stub.uix.screenmanager)

# Now safe to import mobile.main and mobile.src.api
from mobile.main import _version_tuple, _check_version_thread  # noqa: E402
import mobile.main as main_module  # noqa: E402
from mobile.src.api import app_headers, version_headers  # noqa: E402
import mobile.config as mobile_config  # noqa: E402


# ---------------------------------------------------------------------------
# _version_tuple() — parsing
# ---------------------------------------------------------------------------


class TestVersionTuple:
    def test_standard_semver(self):
        assert _version_tuple("2.0.0") == (2, 0, 0)

    def test_two_parts(self):
        assert _version_tuple("1.5") == (1, 5)

    def test_leading_zeros_ignored(self):
        assert _version_tuple("2.0.10") == (2, 0, 10)

    def test_comparison_less_than(self):
        assert _version_tuple("1.9.9") < _version_tuple("2.0.0")

    def test_comparison_equal(self):
        assert _version_tuple("2.0.0") == _version_tuple("2.0.0")

    def test_comparison_greater(self):
        assert _version_tuple("2.1.0") > _version_tuple("2.0.9")

    def test_malformed_returns_zero_tuple(self):
        assert _version_tuple("not-a-version") == (0,)

    def test_empty_returns_zero_tuple(self):
        assert _version_tuple("") == (0,)


# ---------------------------------------------------------------------------
# APP_VERSION sourced from config
# ---------------------------------------------------------------------------


def test_app_version_matches_config():
    """APP_VERSION in main.py must equal config.APP_VERSION, never hardcoded."""
    assert main_module.APP_VERSION == mobile_config.APP_VERSION


# ---------------------------------------------------------------------------
# _check_version_thread() — behaviour under different server responses
# ---------------------------------------------------------------------------


def _run_version_check(server_response: dict) -> None:
    """Helper: run _check_version_thread() synchronously with a mocked API."""
    mock_get_app_version = AsyncMock(return_value=server_response)
    with patch("mobile.src.api.content_client.get_app_version", mock_get_app_version):
        _check_version_thread()


class TestCheckVersionThread:
    def test_upgrade_required_when_below_minimum(self):
        """When APP_VERSION < min_version, the upgrade-required modal fires."""
        with patch.object(main_module, "APP_VERSION", "1.0.0"):
            with patch.object(
                main_module, "_show_upgrade_required_main"
            ) as mock_required, patch.object(
                main_module, "_show_upgrade_banner_main"
            ) as mock_banner:
                _run_version_check({"min_version": "2.0.0", "latest_version": "2.1.0"})

        mock_required.assert_called_once_with("2.0.0")
        mock_banner.assert_not_called()

    def test_upgrade_banner_when_below_latest(self):
        """When min <= APP_VERSION < latest_version, the non-blocking banner fires."""
        with patch.object(main_module, "APP_VERSION", "2.0.0"):
            with patch.object(
                main_module, "_show_upgrade_required_main"
            ) as mock_required, patch.object(
                main_module, "_show_upgrade_banner_main"
            ) as mock_banner:
                _run_version_check({"min_version": "2.0.0", "latest_version": "2.1.0"})

        mock_banner.assert_called_once_with("2.1.0")
        mock_required.assert_not_called()

    def test_no_ui_when_on_latest(self):
        """When APP_VERSION == latest_version, no modal or banner is shown."""
        with patch.object(main_module, "APP_VERSION", "2.1.0"):
            with patch.object(
                main_module, "_show_upgrade_required_main"
            ) as mock_required, patch.object(
                main_module, "_show_upgrade_banner_main"
            ) as mock_banner:
                _run_version_check({"min_version": "2.0.0", "latest_version": "2.1.0"})

        mock_required.assert_not_called()
        mock_banner.assert_not_called()

    def test_network_failure_is_non_fatal(self):
        """A connection error must not raise — app must continue to login screen."""
        mock_fail = AsyncMock(side_effect=Exception("connection refused"))
        with patch("mobile.src.api.content_client.get_app_version", mock_fail):
            # Must not raise
            _check_version_thread()

    def test_missing_keys_use_safe_defaults(self):
        """A response with missing keys must not crash — safe fallback values used."""
        with patch.object(main_module, "APP_VERSION", "2.0.0"):
            with patch.object(main_module, "_show_upgrade_required_main") as mock_required, \
                 patch.object(main_module, "_show_upgrade_banner_main") as mock_banner:
                _run_version_check({})  # empty dict — no min_version, no latest_version

        # min_version defaults to "0.0.0" — 2.0.0 >= 0.0.0, so no upgrade required
        mock_required.assert_not_called()
        # latest_version defaults to APP_VERSION itself — no banner
        mock_banner.assert_not_called()


# ---------------------------------------------------------------------------
# X-App-Version header helpers
# ---------------------------------------------------------------------------


class TestApiHeaders:
    def test_app_headers_includes_x_app_version(self):
        headers = app_headers("some-token")
        assert "X-App-Version" in headers

    def test_app_headers_x_app_version_matches_config(self):
        headers = app_headers("some-token")
        assert headers["X-App-Version"] == mobile_config.APP_VERSION

    def test_version_headers_includes_x_app_version(self):
        headers = version_headers()
        assert "X-App-Version" in headers

    def test_version_headers_has_no_authorization(self):
        headers = version_headers()
        assert "Authorization" not in headers

    def test_app_headers_includes_authorization(self):
        headers = app_headers("tok-abc")
        assert headers["Authorization"] == "Bearer tok-abc"
