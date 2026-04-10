"""
backend/src/core/middleware.py

Application-level HTTP middleware (beyond correlation ID and CORS).

AppVersionMiddleware
  Checks the ``X-App-Version`` header sent by the mobile client on every request.
  If the header is present and the version is older than MINIMUM_SUPPORTED_APP_VERSION
  (read from config at startup), returns HTTP 426 Upgrade Required so the app can
  show an "update required" screen immediately instead of producing silent parse errors.

  Behaviour:
    - Header absent        → pass through (web / API clients don't send it).
    - Header present, old  → 426 with error body.
    - Header unparseable   → pass through (be lenient; do not break unknown clients).
    - Header present, ok   → pass through.

  The minimum version is controlled by ``MINIMUM_SUPPORTED_APP_VERSION`` in config.py
  so ops can bump it without a code deploy.
"""

from __future__ import annotations

from collections.abc import Callable

from config import settings
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

log = get_logger("middleware")


def _parse_version(version_str: str) -> tuple[int, ...] | None:
    """
    Parse a ``MAJOR.MINOR.PATCH`` string into an integer tuple.

    Returns None if the string cannot be parsed so the middleware stays lenient.
    """
    try:
        parts = tuple(int(x) for x in version_str.strip().split("."))
        if len(parts) < 2:
            return None
        return parts
    except (ValueError, AttributeError):
        return None


class AppVersionMiddleware(BaseHTTPMiddleware):
    """
    Reject requests from mobile clients whose app version is below the minimum.

    Reads MINIMUM_SUPPORTED_APP_VERSION from config at request time so that
    a config change (e.g. via env var reload) takes effect without a process
    restart.  The parsed tuple is re-computed each request, but the overhead
    is negligible (a single string split).

    Skips non-API paths (health, metrics) so infrastructure tooling is unaffected.
    """

    def __init__(self, app, minimum_version: str | None = None, **kwargs) -> None:
        super().__init__(app, **kwargs)
        # Optional override for testing — normally read from settings at request time.
        self._override: str | None = minimum_version

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health/metrics paths — infra probes never send the header.
        if request.url.path in ("/healthz", "/readyz", "/health", "/metrics"):
            return await call_next(request)

        raw_minimum = self._override or settings.MINIMUM_SUPPORTED_APP_VERSION
        minimum = _parse_version(raw_minimum)

        version_header = request.headers.get("X-App-Version")
        if version_header and minimum is not None:
            client_version = _parse_version(version_header)
            if client_version is not None and client_version < minimum:
                log.info(
                    "app_version_rejected",
                    client_version=version_header,
                    minimum=raw_minimum,
                )
                return JSONResponse(
                    status_code=426,
                    content={
                        "error": "app_version_too_old",
                        "detail": (
                            f"App version {version_header} is no longer supported. "
                            "Please update to continue."
                        ),
                        "minimum_version": raw_minimum,
                        "upgrade_url": "https://studybuddy.app/upgrade",
                    },
                )

        return await call_next(request)
