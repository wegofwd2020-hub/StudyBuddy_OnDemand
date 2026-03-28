"""
backend/src/core/observability.py

Prometheus metrics, CorrelationIdMiddleware, /health and /metrics endpoints.

Metrics exported:
  sb_requests_total          counter  (method, path, status)
  sb_request_duration_seconds histogram (method, path)
  sb_db_pool_connections     gauge    (state: min|max|size|free)
  sb_redis_connected         gauge
  sb_auth_exchanges_total    counter  (track: student|teacher)
  sb_auth_failures_total     counter  (reason)
  sb_events_total            counter  (category, event_type)
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextvars import ContextVar

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger import get_logger

log = get_logger("observability")

# ── Context var for correlation ID ────────────────────────────────────────────
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# ── Prometheus metrics ────────────────────────────────────────────────────────
requests_total = Counter(
    "sb_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

request_duration = Histogram(
    "sb_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

db_pool_connections = Gauge(
    "sb_db_pool_connections",
    "AsyncPG pool connection counts",
    ["state"],
)

redis_connected = Gauge(
    "sb_redis_connected",
    "1 if Redis is reachable, 0 otherwise",
)

auth_exchanges_total = Counter(
    "sb_auth_exchanges_total",
    "Successful auth token exchanges",
    ["track"],
)

auth_failures_total = Counter(
    "sb_auth_failures_total",
    "Failed authentication attempts",
    ["reason"],
)

events_total = Counter(
    "sb_events_total",
    "Application events emitted",
    ["category", "event_type"],
)


# ── Correlation ID middleware ─────────────────────────────────────────────────

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Inject a UUID correlation ID into every request/response cycle.

    - Reads X-Correlation-Id from the incoming request (if provided by a caller).
    - Generates a new UUID if not provided.
    - Stores in contextvars so all log calls in the same request include it.
    - Sets X-Correlation-Id response header.
    - Stores on request.state.correlation_id for use in error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        token = correlation_id_var.set(cid)
        request.state.correlation_id = cid

        try:
            response: Response = await call_next(request)
        finally:
            correlation_id_var.reset(token)

        response.headers["X-Correlation-Id"] = cid
        return response


# ── Health + metrics router ───────────────────────────────────────────────────

router = APIRouter(tags=["observability"])


@router.get("/health", include_in_schema=True)
async def health_check(request: Request) -> dict:
    """
    Deep health check: verifies DB and Redis connectivity.

    Returns HTTP 200 if all dependencies are healthy.
    Returns HTTP 503 if any dependency is unreachable.
    """
    from config import settings

    db_status = "error"
    redis_status = "error"

    # ── DB check ──────────────────────────────────────────────────────────────
    try:
        pool = getattr(request.app.state, "pool", None)
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_status = "ok"
            # Update pool metrics
            db_pool_connections.labels(state="size").set(pool.get_size())
            db_pool_connections.labels(state="free").set(pool.get_idle_size())
            db_pool_connections.labels(state="min").set(settings.DATABASE_POOL_MIN)
            db_pool_connections.labels(state="max").set(settings.DATABASE_POOL_MAX)
    except Exception as exc:
        log.error("health_check_db_failed", error=str(exc))

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis is not None:
            await redis.ping()
            redis_status = "ok"
            redis_connected.set(1)
        else:
            redis_connected.set(0)
    except Exception as exc:
        log.error("health_check_redis_failed", error=str(exc))
        redis_connected.set(0)

    payload = {
        "db": db_status,
        "redis": redis_status,
        "version": settings.APP_VERSION,
    }

    if db_status != "ok" or redis_status != "ok":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "detail": payload,
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )

    return payload


@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint(request: Request) -> PlainTextResponse:
    """
    Prometheus metrics endpoint.

    Protected by Bearer METRICS_TOKEN.  nginx further restricts access
    to the internal IP range (10.0.0.0/8) in production.
    """
    from config import settings

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header[7:] != settings.METRICS_TOKEN:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "Valid METRICS_TOKEN required.",
                "correlation_id": getattr(request.state, "correlation_id", ""),
            },
        )

    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
