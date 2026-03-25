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

Health and metrics mounted at root (no /api/v1 prefix):
  - GET /health
  - GET /metrics
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from src.core.observability import CorrelationIdMiddleware, router as obs_router
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
    app.state.pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=settings.DATABASE_POOL_MIN,
        max_size=settings.DATABASE_POOL_MAX,
        command_timeout=30,
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
    allow_methods=["*"],
    allow_headers=["*"],
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

from src.auth.router import router as auth_router
from src.auth.admin_router import router as admin_auth_router
from src.account.router import router as account_router
from src.curriculum.router import router as curriculum_router
from src.content.router import router as content_router
from src.progress.router import router as progress_router
from src.student.router import router as student_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(curriculum_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")

log.info("routers_registered")
