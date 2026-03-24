"""
backend/config.py

All configuration is sourced from environment variables via pydantic-settings.
Missing required secrets cause an immediate startup failure — no silent defaults.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_MIN: int = 5
    DATABASE_POOL_MAX: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 10

    # ── JWT (student / teacher) ───────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Admin JWT (internal product team) ────────────────────────────────────
    ADMIN_JWT_SECRET: str
    ADMIN_JWT_EXPIRE_MINUTES: int = 60

    # ── Auth0 ────────────────────────────────────────────────────────────────
    AUTH0_DOMAIN: str
    AUTH0_JWKS_URL: str
    AUTH0_STUDENT_CLIENT_ID: str
    AUTH0_TEACHER_CLIENT_ID: str

    # Auth0 Management API
    AUTH0_MGMT_CLIENT_ID: str
    AUTH0_MGMT_CLIENT_SECRET: str
    AUTH0_MGMT_API_URL: str

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Sentry (optional) ─────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None

    # ── Observability ─────────────────────────────────────────────────────────
    METRICS_TOKEN: str

    # ── Content Store ─────────────────────────────────────────────────────────
    CONTENT_STORE_PATH: str = "/data/content"

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: Optional[str] = None

    @property
    def effective_celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    # ── Cache TTLs ────────────────────────────────────────────────────────────
    JWKS_CACHE_TTL_HOURS: int = 24

    # ── Feature flags ─────────────────────────────────────────────────────────
    REVIEW_AUTO_APPROVE: bool = False

    # ── Validation ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def secrets_must_differ(self) -> "Settings":
        if self.JWT_SECRET == self.ADMIN_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET and ADMIN_JWT_SECRET must be different values."
            )
        return self

    @field_validator("JWT_SECRET", "ADMIN_JWT_SECRET", mode="before")
    @classmethod
    def minimum_secret_length(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError(
                f"{info.field_name} must be at least 32 characters long."
            )
        return v


settings = Settings()
