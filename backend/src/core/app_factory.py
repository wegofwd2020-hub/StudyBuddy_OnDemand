"""
backend/src/core/app_factory.py

Application factory for the StudyBuddy OnDemand FastAPI app.

Separates app *creation* from app *registration* so that:
  - Routers never need to import from main.py (no circular imports).
  - Tests can call create_app() independently.
  - Adding a new router means editing _register_routers() only.

Entry point (main.py) is now just:
  from src.core.app_factory import create_app
  app = create_app()
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

from slowapi.errors import RateLimitExceeded

from src.core.limiter import limiter
from src.core.middleware import AppVersionMiddleware
from src.core.observability import CorrelationIdMiddleware
from src.core.observability import router as obs_router
from src.utils.logger import get_logger

log = get_logger("main")


# ── Sentry (optional, initialised once at import time) ────────────────────────


def _init_sentry() -> None:
    """Initialise Sentry SDK if SENTRY_DSN is configured."""
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    def _before_send(event: dict, hint: dict) -> dict:
        """Strip PII before sending to Sentry."""
        if "request" in event:
            event["request"].pop("data", None)
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

    _total_db_conns = settings.DATABASE_POOL_MAX * settings.WORKER_COUNT
    log.info(
        "connection_pool_arithmetic",
        pool_max=settings.DATABASE_POOL_MAX,
        workers=settings.WORKER_COUNT,
        total_connections=_total_db_conns,
        pgbouncer_pool_size=settings.PGBOUNCER_POOL_SIZE,
        headroom=settings.PGBOUNCER_POOL_SIZE - _total_db_conns,
    )

    # statement_cache_size=0 required for PgBouncer transaction-pooling mode.
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

    app.state.redis = await aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=False,
    )
    log.info("redis_pool_created", url=settings.REDIS_URL.split("@")[-1])

    from src.core.storage import LocalStorage, S3Storage

    if settings.STORAGE_BACKEND == "s3":
        if not settings.S3_BUCKET_NAME:
            raise RuntimeError("S3_BUCKET_NAME must be set when STORAGE_BACKEND=s3")
        app.state.storage = S3Storage(
            bucket=settings.S3_BUCKET_NAME,
            prefix=settings.S3_KEY_PREFIX,
        )
        log.info(
            "storage_backend_s3",
            bucket=settings.S3_BUCKET_NAME,
            prefix=settings.S3_KEY_PREFIX or "(none)",
        )
    else:
        app.state.storage = LocalStorage(root=settings.CONTENT_STORE_PATH)
        log.info("storage_backend_local", root=settings.CONTENT_STORE_PATH)

    log.info("startup_complete")
    yield

    log.info("shutdown_begin")
    await app.state.pool.close()
    await app.state.redis.close()
    log.info("shutdown_complete")


# ── Exception handlers ────────────────────────────────────────────────────────


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        cid = getattr(request.state, "correlation_id", "")
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "detail": "Too many requests. Please try again later.",
                "correlation_id": cid,
            },
        )


# ── Middleware ────────────────────────────────────────────────────────────────


def _register_middleware(app: FastAPI) -> None:
    # Middleware is applied in reverse registration order (last added = outermost).
    # CorrelationId must be outermost so correlation_id is available to all layers.
    # AppVersion runs inside CorrelationId so 426 responses carry a correlation ID.
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(AppVersionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Correlation-Id", "X-Requested-With"],
        expose_headers=["X-Correlation-Id"],
    )


# ── Routers ───────────────────────────────────────────────────────────────────


def _register_routers(app: FastAPI) -> None:
    # Lazy imports inside this function body avoid circular imports:
    # routers import from src.core.* but never from main.py.
    from src.account.router import router as account_router
    from src.admin.build_reports import router as ci_reports_router
    from src.admin.demo_accounts import router as demo_admin_router
    from src.admin.demo_teacher_accounts import router as demo_teacher_admin_router
    from src.admin.retention_router import router as admin_retention_router
    from src.admin.router import router as admin_router
    from src.analytics.router import router as analytics_router
    from src.auth.admin_router import router as admin_auth_router
    from src.auth.router import router as auth_router
    from src.content.router import router as content_router
    from src.curriculum.router import router as curriculum_router
    from src.demo.router import router as demo_router
    from src.demo.teacher_router import router as demo_teacher_router
    from src.feedback.router import router as feedback_router
    from src.notifications.router import router as notifications_router
    from src.progress.router import router as progress_router
    from src.reports.router import router as reports_router
    from src.school.content_router import router as school_content_router
    from src.school.limits_router import router as school_limits_router
    from src.school.pipeline_router import router as school_pipeline_router
    from src.school.retention_router import router as school_retention_router
    from src.school.router import router as school_router
    from src.school.storage_router import router as school_storage_router
    from src.school.subscription_router import router as school_subscription_router
    from src.student.router import router as student_router
    from src.subscription.router import router as subscription_router
    from src.teacher.subscription_router import router as teacher_subscription_router

    # Health + metrics at root (no /api/v1 prefix).
    app.include_router(obs_router)

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
    app.include_router(admin_retention_router, prefix="/api/v1")
    app.include_router(ci_reports_router, prefix="/api/v1")
    app.include_router(school_router, prefix="/api/v1")
    app.include_router(school_content_router, prefix="/api/v1")
    app.include_router(school_subscription_router, prefix="/api/v1")
    app.include_router(teacher_subscription_router, prefix="/api/v1")
    app.include_router(school_limits_router, prefix="/api/v1")
    app.include_router(school_pipeline_router, prefix="/api/v1")
    app.include_router(school_retention_router, prefix="/api/v1")
    app.include_router(school_storage_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(demo_router, prefix="/api/v1")
    app.include_router(demo_teacher_router, prefix="/api/v1")
    app.include_router(demo_admin_router, prefix="/api/v1")
    app.include_router(demo_teacher_admin_router, prefix="/api/v1")

    if settings.APP_ENV == "development":
        from src.auth.dev_router import router as dev_router

        app.include_router(dev_router, prefix="/api/v1")
        log.info("dev_router_registered")

    log.info("routers_registered")


# ── Factory ───────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """
    Build and return the configured FastAPI application.

    Called once per worker process by main.py:
      app = create_app()
    """
    _init_sentry()

    app = FastAPI(
        title="StudyBuddy OnDemand API",
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app
