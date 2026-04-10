"""
tests/test_app_version_middleware.py

Tests for AppVersionMiddleware in src/core/middleware.py.

Covers:
  - No X-App-Version header → pass through (web/API clients)
  - Version >= minimum → pass through
  - Version == minimum exactly → pass through (boundary)
  - Version < minimum → HTTP 426 with structured body
  - Malformed version string → pass through (lenient)
  - Health/metrics paths always pass through regardless of version
  - 426 body contains minimum_version and upgrade_url
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.middleware import AppVersionMiddleware, _parse_version


# ── _parse_version() unit tests ───────────────────────────────────────────────


def test_parse_version_valid_semver():
    assert _parse_version("2.0.0") == (2, 0, 0)


def test_parse_version_two_parts():
    assert _parse_version("2.1") == (2, 1)


def test_parse_version_with_whitespace():
    assert _parse_version("  3.1.4  ") == (3, 1, 4)


def test_parse_version_non_numeric_returns_none():
    assert _parse_version("latest") is None


def test_parse_version_empty_returns_none():
    assert _parse_version("") is None


def test_parse_version_single_part_returns_none():
    assert _parse_version("2") is None


# ── Middleware integration tests ──────────────────────────────────────────────


def _make_app(minimum: str = "2.0.0") -> FastAPI:
    """
    Build a minimal FastAPI app with AppVersionMiddleware and one test route.

    Passes minimum_version directly to the middleware so no settings patching
    is needed — Starlette builds the middleware stack lazily and would read the
    live (unpatched) settings by the time the first request arrives.
    """
    app = FastAPI()
    app.add_middleware(AppVersionMiddleware, minimum_version=minimum)

    @app.get("/api/v1/test")
    async def test_route():
        return {"ok": True}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics():
        return {"metrics": "data"}

    return app


@pytest.fixture
def client():
    app = _make_app(minimum="2.0.0")
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_no_version_header_passes_through(client):
    """Requests without X-App-Version must not be rejected."""
    resp = client.get("/api/v1/test")
    assert resp.status_code == 200


def test_version_above_minimum_passes_through(client):
    resp = client.get("/api/v1/test", headers={"X-App-Version": "3.0.0"})
    assert resp.status_code == 200


def test_version_equal_to_minimum_passes_through(client):
    """Boundary: version exactly equal to minimum must be accepted."""
    resp = client.get("/api/v1/test", headers={"X-App-Version": "2.0.0"})
    assert resp.status_code == 200


def test_version_below_minimum_returns_426(client):
    resp = client.get("/api/v1/test", headers={"X-App-Version": "1.9.9"})
    assert resp.status_code == 426


def test_426_body_has_required_fields(client):
    resp = client.get("/api/v1/test", headers={"X-App-Version": "1.0.0"})
    body = resp.json()
    assert body["error"] == "app_version_too_old"
    assert "minimum_version" in body
    assert body["minimum_version"] == "2.0.0"
    assert "upgrade_url" in body


def test_malformed_version_header_passes_through(client):
    """Invalid format must not cause a 426 — be lenient."""
    resp = client.get("/api/v1/test", headers={"X-App-Version": "not-a-version"})
    assert resp.status_code == 200


def test_major_version_bump_rejected(client):
    """1.x.x < 2.0.0 for all x."""
    resp = client.get("/api/v1/test", headers={"X-App-Version": "1.99.99"})
    assert resp.status_code == 426


def test_minor_version_below_minimum():
    """2.0.1 >= 2.1.0 is False — test minor version enforcement."""
    app = _make_app(minimum="2.1.0")
    with TestClient(app) as c:
        resp = c.get("/api/v1/test", headers={"X-App-Version": "2.0.9"})
        assert resp.status_code == 426

        resp2 = c.get("/api/v1/test", headers={"X-App-Version": "2.1.0"})
        assert resp2.status_code == 200


def test_healthz_always_passes_through_old_version(client):
    """/healthz must never return 426 — infra probes don't send the header."""
    resp = client.get("/healthz", headers={"X-App-Version": "0.0.1"})
    assert resp.status_code == 200


def test_metrics_always_passes_through_old_version(client):
    resp = client.get("/metrics", headers={"X-App-Version": "0.0.1"})
    assert resp.status_code == 200
