"""
backend/src/core/observability.py

Prometheus metrics, CorrelationIdMiddleware, and observability endpoints.

Endpoints (mounted at root — no /api/v1 prefix):
  GET /healthz   liveness probe   — always 200 if the process is up
  GET /readyz    readiness probe  — 200 if DB + Redis are reachable, 503 otherwise
  GET /health    alias for /readyz (backwards-compatible)
  GET /metrics   Prometheus scrape target (requires METRICS_TOKEN)

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

import time
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

celery_queue_depth = Gauge(
    "sb_celery_queue_depth",
    "Number of tasks waiting in each Celery queue",
    ["queue"],
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


# ── Prometheus per-request middleware ────────────────────────────────────────


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Increment sb_requests_total and observe sb_request_duration_seconds for
    every HTTP request. Path label uses the FastAPI route template
    (e.g. "/api/v1/content/{unit_id}/lesson") so cardinality stays bounded —
    we never label by the raw URL, which would explode the time series count.

    Excludes /metrics itself (would self-spam) and /healthz (constant noise).
    """

    EXCLUDE_PATHS = frozenset(
        {
            "/metrics",
            "/healthz",
            "/readyz",
            "/health",
            "/health/deep",
            # /api/v1 aliases of the health probes (see api_health_router below)
            "/api/v1/healthz",
            "/api/v1/readyz",
            "/api/v1/health",
            "/api/v1/health/deep",
        }
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        status = 500
        try:
            response: Response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            handler = "unmatched"
            if route is not None:
                handler = getattr(route, "path", None) or getattr(route, "name", "unmatched")
            requests_total.labels(method=request.method, path=handler, status=str(status)).inc()
            request_duration.labels(method=request.method, path=handler).observe(elapsed)


# ── Health + metrics router ───────────────────────────────────────────────────

router = APIRouter(tags=["observability"])


@router.get("/healthz", include_in_schema=False)
async def liveness_check() -> dict:
    """
    Liveness probe — always 200 if the process is running.

    Kubernetes/ECS: use this for livenessProbe. A failure here causes a pod restart.
    This endpoint intentionally does NOT check external dependencies.
    """
    return {"status": "ok"}


async def _readiness_check(request: Request) -> dict:
    """
    Shared readiness logic: verifies DB and Redis connectivity.

    Returns the payload dict if healthy; raises HTTP 503 if not.
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
        # Which commit is actually running (#583). APP_VERSION is a human label
        # set per environment; this is the build identity.
        "build": settings.BUILD_ID,
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


@router.get("/readyz", include_in_schema=True)
async def readiness_check(request: Request) -> dict:
    """
    Readiness probe — 200 if DB and Redis are reachable, 503 otherwise.

    Kubernetes/ECS: use this for readinessProbe. A failure here removes the pod
    from the load balancer until dependencies recover.
    """
    return await _readiness_check(request)


@router.get("/health", include_in_schema=True)
async def health_check(request: Request) -> dict:
    """
    Deep health check alias for /readyz (backwards-compatible).

    Returns HTTP 200 if all dependencies are healthy.
    Returns HTTP 503 if any dependency is unreachable.
    """
    return await _readiness_check(request)


@router.get("/health/deep", include_in_schema=True)
async def deep_health_check(request: Request) -> dict:
    """
    Comprehensive infrastructure health check — tests all 6 services.

    Returns HTTP 200 if all services are operational.
    Returns HTTP 503 if any service is unreachable (degraded or down).

    Tests:
      - API (this service)
      - Web (Next.js frontend)
      - DB (PostgreSQL)
      - Redis (cache)
      - PgBouncer (connection pooler)
      - Auth0 (if configured)
    """
    import asyncio

    import httpx
    from config import settings

    services = {
        "api": "ok",  # If we're responding, API is up
        "web": "error",
        "db": "error",
        "redis": "error",
        "pgbouncer": "error",
        "auth0": "ok" if not settings.AUTH0_DOMAIN else "error",
    }

    # ── DB check (direct, not pooled) ─────────────────────────────────────
    try:
        pool = getattr(request.app.state, "pool", None)
        if pool is not None:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            services["db"] = "ok"
    except Exception as exc:
        log.error("health_deep_db_failed", error=str(exc))

    # ── Redis check ───────────────────────────────────────────────────────
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis is not None:
            await redis.ping()
            services["redis"] = "ok"
    except Exception as exc:
        log.error("health_deep_redis_failed", error=str(exc))

    # ── PgBouncer check (via settings.DATABASE_URL if different) ──────────
    try:
        from asyncpg import connect
        # Connect to PgBouncer port if configured
        pgbouncer_url = str(settings.DATABASE_URL).replace(":5432/", ":6432/")
        pgbouncer_conn = await asyncio.wait_for(connect(pgbouncer_url), timeout=2.0)
        await pgbouncer_conn.close()
        services["pgbouncer"] = "ok"
    except Exception as exc:
        log.error("health_deep_pgbouncer_failed", error=str(exc))

    # ── Web (nginx/frontend) check ────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Check if web container is responding via localhost (for internal check)
            # or via the configured domain
            web_url = "http://127.0.0.1:3000/" if settings.ENV == "dev" else f"https://{settings.PUBLIC_URL}/"
            resp = await client.get(web_url, follow_redirects=False)
            # Accept 200, 301, 302 (redirects OK) - just check if server responds
            if resp.status_code < 500:
                services["web"] = "ok"
    except Exception as exc:
        log.error("health_deep_web_failed", error=str(exc))

    # ── Auth0 check (if configured) ───────────────────────────────────────
    if settings.AUTH0_DOMAIN:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                auth0_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration"
                resp = await client.get(auth0_url)
                if resp.status_code == 200:
                    services["auth0"] = "ok"
        except Exception as exc:
            log.error("health_deep_auth0_failed", error=str(exc))

    # ── Determine overall status ──────────────────────────────────────────
    critical = ["api", "db", "redis", "pgbouncer", "web"]
    critical_ok = all(services[s] == "ok" for s in critical)
    all_ok = all(v == "ok" for v in services.values())

    overall_status = "operational" if all_ok else ("degraded" if critical_ok else "down")

    payload = {
        "status": overall_status,
        "services": services,
        "version": settings.APP_VERSION,
        "build": settings.BUILD_ID,
    }

    # Return 503 if any critical service is down
    if not critical_ok:
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


# ── /api/v1 health aliases ────────────────────────────────────────────────────
# The probes above are mounted at root (obs_router). nginx proxies both /healthz
# and /api/v1/* to the backend, but the health routes never existed under the
# /api/v1 prefix — so /api/v1/health fell through to the Next.js frontend (404).
# Re-expose liveness + readiness + deep health under /api/v1 (included with
# prefix="/api/v1" in app_factory) for callers that assume the API prefix. The
# /api/v1 paths are added to PrometheusMiddleware.EXCLUDE_PATHS above so probe
# traffic stays out of the request metrics, exactly like the root paths.
#
# All three are include_in_schema=False: these aliases are operational probes,
# not part of the public API contract, so they must stay OUT of the OpenAPI
# schema (the root /health + /readyz remain the documented entries). Keeping
# them unexported avoids drifting the generated TypeScript types.
api_health_router = APIRouter(tags=["observability"])
api_health_router.add_api_route(
    "/healthz", liveness_check, methods=["GET"], include_in_schema=False
)
api_health_router.add_api_route(
    "/readyz", readiness_check, methods=["GET"], include_in_schema=False
)
api_health_router.add_api_route("/health", health_check, methods=["GET"], include_in_schema=False)
api_health_router.add_api_route(
    "/health/deep", deep_health_check, methods=["GET"], include_in_schema=True
)
