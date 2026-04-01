"""
backend/main.py

FastAPI application entry point.

Lifespan:
  - Creates asyncpg connection pool (min=5, max=20) on startup
  - Creates aioredis pool on startup
  - Closes both on shutdown

Middleware:
  - CorrelationIdMiddleware (UUID per request; X-Correlation-Id header)
  - CORSMiddleware

Routers registered at /api/v1 prefix:
  - auth (student + teacher)
  - admin_auth
  - account
  - curriculum
  - content
  - progress
  - student
  - notifications
  - analytics
  - school
  - feedback
  - reports

Health and metrics mounted at root (no /api/v1 prefix):
  - GET /health
  - GET /metrics
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from config import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.observability import CorrelationIdMiddleware
from src.core.observability import router as obs_router
from src.utils.logger import get_logger

log = get_logger("main")


# ── Sentry initialisation (optional) ─────────────────────────────────────────

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    def _before_send(event: dict, hint: dict) -> dict:
        """Strip PII before sending to Sentry."""
        # Remove request body (may contain passwords).
        if "request" in event:
            event["request"].pop("data", None)
        # Scrub known PII keys from extra/contexts.
        for key in ("email", "password", "token", "refresh_token", "id_token"):
            event.get("extra", {}).pop(key, None)
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(),
        ],
        traces_sample_rate=0.05,
        send_default_pii=False,
        before_send=_before_send,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
    )
    log.info("sentry_initialised", dsn_prefix=settings.SENTRY_DSN[:30])


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and close asyncpg + aioredis pools for the lifetime of each worker."""
    log.info(
        "startup_begin",
        app_env=settings.APP_ENV,
        version=settings.APP_VERSION,
    )

    # Asyncpg pool — one pool per worker process.
    # statement_cache_size=0 is required when routing through PgBouncer in
    # transaction-pooling mode; prepared statements are not preserved across
    # connections in that mode and would cause InvalidCachedStatementError.
    app.state.pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=settings.DATABASE_POOL_MIN,
        max_size=settings.DATABASE_POOL_MAX,
        command_timeout=30,
        statement_cache_size=0,
    )
    log.info(
        "db_pool_created",
        min_size=settings.DATABASE_POOL_MIN,
        max_size=settings.DATABASE_POOL_MAX,
    )

    # aioredis pool.
    app.state.redis = await aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=False,
    )
    log.info("redis_pool_created", url=settings.REDIS_URL.split("@")[-1])

    log.info("startup_complete")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("shutdown_begin")
    await app.state.pool.close()
    await app.state.redis.close()
    log.info("shutdown_complete")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="StudyBuddy OnDemand API",
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-Id", "X-Requested-With"],
    expose_headers=["X-Correlation-Id"],
)

# ── Global exception handlers — never leak stack traces ──────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Convert HTTPException to the standard error envelope:
      {"error": "...", "detail": "...", "correlation_id": "..."}

    If exc.detail is already a dict with an "error" key (as raised by our routers),
    return it directly so the response shape is consistent.
    """
    cid = getattr(request.state, "correlation_id", "")
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = {**exc.detail, "correlation_id": cid}
    else:
        content = {
            "error": "http_error",
            "detail": str(exc.detail),
            "correlation_id": cid,
        }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers or {},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    cid = getattr(request.state, "correlation_id", "")
    log.error("unhandled_exception", error=str(exc), correlation_id=cid, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
            "correlation_id": cid,
        },
    )


# ── Health + metrics (root — no /api/v1 prefix) ───────────────────────────────

app.include_router(obs_router)

# ── API routers ───────────────────────────────────────────────────────────────

from src.account.router import router as account_router  # noqa: E402
from src.admin.build_reports import router as ci_reports_router  # noqa: E402
from src.demo.router import router as demo_router  # noqa: E402
from src.demo.teacher_router import router as demo_teacher_router  # noqa: E402
from src.admin.demo_accounts import router as demo_admin_router  # noqa: E402
from src.admin.demo_teacher_accounts import router as demo_teacher_admin_router  # noqa: E402
from src.admin.router import router as admin_router  # noqa: E402
from src.analytics.router import router as analytics_router  # noqa: E402
from src.auth.admin_router import router as admin_auth_router  # noqa: E402
from src.auth.router import router as auth_router  # noqa: E402
from src.content.router import router as content_router  # noqa: E402
from src.curriculum.router import router as curriculum_router  # noqa: E402
from src.feedback.router import router as feedback_router  # noqa: E402
from src.notifications.router import router as notifications_router  # noqa: E402
from src.progress.router import router as progress_router  # noqa: E402
from src.reports.router import router as reports_router  # noqa: E402
from src.school.router import router as school_router  # noqa: E402
from src.school.pipeline_router import router as school_pipeline_router  # noqa: E402
from src.school.subscription_router import router as school_subscription_router  # noqa: E402
from src.school.limits_router import router as school_limits_router  # noqa: E402
from src.school.content_router import router as school_content_router  # noqa: E402
from src.student.router import router as student_router  # noqa: E402
from src.subscription.router import router as subscription_router  # noqa: E402
from src.private_teacher.router import router as private_teacher_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(curriculum_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(ci_reports_router, prefix="/api/v1")
app.include_router(school_router, prefix="/api/v1")
app.include_router(school_pipeline_router, prefix="/api/v1")
app.include_router(school_subscription_router, prefix="/api/v1")
app.include_router(school_limits_router, prefix="/api/v1")
app.include_router(school_content_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(demo_teacher_router, prefix="/api/v1")
app.include_router(demo_admin_router, prefix="/api/v1")
app.include_router(demo_teacher_admin_router, prefix="/api/v1")
app.include_router(private_teacher_router, prefix="/api/v1")

if settings.APP_ENV == "development":
    from src.auth.dev_router import router as dev_router

    app.include_router(dev_router, prefix="/api/v1")
    log.info("dev_router_registered")

log.info("routers_registered")
