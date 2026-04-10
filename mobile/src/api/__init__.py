"""
mobile/src/api/__init__.py

Shared HTTP header helpers for all API clients.

Every request to the backend includes X-App-Version so the server can
enforce a minimum supported version and return 426 Upgrade Required when
the app is too old (see backend/src/core/middleware.py).
"""

from __future__ import annotations

try:
    from mobile.config import APP_VERSION  # type: ignore
except ImportError:
    import os
    APP_VERSION = os.environ.get("APP_VERSION", "0.0.0")


def app_headers(token: str) -> dict[str, str]:
    """Return Authorization + X-App-Version headers for authenticated requests."""
    return {
        "Authorization": f"Bearer {token}",
        "X-App-Version": APP_VERSION,
    }


def version_headers() -> dict[str, str]:
    """Return X-App-Version header for unauthenticated requests."""
    return {"X-App-Version": APP_VERSION}
