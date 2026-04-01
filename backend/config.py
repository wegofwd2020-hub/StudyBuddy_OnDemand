"""
backend/config.py

All configuration is sourced from environment variables via pydantic-settings.
Missing required secrets cause an immediate startup failure — no silent defaults.
"""

from __future__ import annotations

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
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Sentry (optional) ─────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None

    # ── Observability ─────────────────────────────────────────────────────────
    METRICS_TOKEN: str

    # ── Content Store ─────────────────────────────────────────────────────────
    CONTENT_STORE_PATH: str = "/data/content"

    # ── Stripe ────────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_MONTHLY_ID: str | None = None
    STRIPE_PRICE_ANNUAL_ID: str | None = None

    # ── Push Notifications (FCM) ───────────────────────────────────────────────
    FCM_SERVER_KEY: str | None = None

    # ── AWS / CDN ─────────────────────────────────────────────────────────────
    S3_BUCKET_NAME: str | None = None
    CLOUDFRONT_DISTRIBUTION_ID: str | None = None

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str | None = None

    # ── Dictionary (Phase 7) ─────────────────────────────────────────────────
    MW_API_KEY: str | None = None  # Merriam-Webster Collegiate Dictionary API key

    # ── Academic year (Phase 8) ───────────────────────────────────────────────
    # Format: "MM-DD" (e.g. "09-01" for September 1st).
    # Celery Beat task runs daily and promotes grades when today matches.
    GRADE_PROMOTION_DATE: str | None = None

    # ── Email (Phase 8) ───────────────────────────────────────────────────────
    SENDGRID_API_KEY: str | None = None
    EMAIL_FROM: str = "noreply@studybuddy.app"

    # ── SMTP (demo email via Gmail) ───────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None      # Gmail address (e.g. hello@studybuddy.app)
    SMTP_PASSWORD: str | None = None  # Gmail App Password (not account password)
    SMTP_FROM_NAME: str = "StudyBuddy"

    # ── Demo accounts ─────────────────────────────────────────────────────────
    DEMO_ACCOUNT_TTL_HOURS: int = 24
    DEMO_VERIFICATION_TOKEN_TTL_MINUTES: int = 60
    DEMO_RESEND_COOLDOWN_MINUTES: int = 5
    DEMO_MAX_ACTIVE: int = 100             # hard cap on concurrent active demo student accounts

    DEMO_TEACHER_ACCOUNT_TTL_HOURS: int = 48
    DEMO_TEACHER_MAX_ACTIVE: int = 50      # hard cap on concurrent active demo teacher accounts
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def effective_celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    # ── Cache TTLs ────────────────────────────────────────────────────────────
    # 1 hour matches the typical Auth0 JWKS rotation window. 24 hours risks
    # serving a stale key set for too long after a key rotation event.
    JWKS_CACHE_TTL_HOURS: int = 1

    # ── GitHub CI integration (optional) ─────────────────────────────────────
    # GITHUB_REPO:  "owner/repo"  e.g. "wegofwd2020-hub/StudyBuddy_OnDemand"
    # GITHUB_TOKEN: Personal Access Token or Fine-grained token with Actions:read
    #               Without a token the GitHub API allows 60 unauthenticated
    #               requests/hour per IP — sufficient for a low-traffic admin panel.
    GITHUB_REPO: str | None = None
    GITHUB_TOKEN: str | None = None

    # ── School pipeline quotas (runs per calendar month per school) ──────────────
    SCHOOL_PIPELINE_QUOTA_STARTER: int = 3
    SCHOOL_PIPELINE_QUOTA_PROFESSIONAL: int = 10
    SCHOOL_PIPELINE_QUOTA_ENTERPRISE: int = 9999

    # ── School subscription — Stripe price IDs ────────────────────────────────
    STRIPE_SCHOOL_PRICE_STARTER_ID: str | None = None
    STRIPE_SCHOOL_PRICE_PROFESSIONAL_ID: str | None = None
    STRIPE_SCHOOL_PRICE_ENTERPRISE_ID: str | None = None

    # ── School seat limits by plan ────────────────────────────────────────────
    SCHOOL_SEATS_STARTER_STUDENTS: int = 30
    SCHOOL_SEATS_STARTER_TEACHERS: int = 3
    SCHOOL_SEATS_PROFESSIONAL_STUDENTS: int = 150
    SCHOOL_SEATS_PROFESSIONAL_TEACHERS: int = 10
    SCHOOL_SEATS_ENTERPRISE_STUDENTS: int = 9999
    SCHOOL_SEATS_ENTERPRISE_TEACHERS: int = 9999

    # ── Private teacher plan limits ───────────────────────────────────────────
    PRIVATE_TEACHER_PLAN_BASIC_PIPELINE_QUOTA: int = 2
    PRIVATE_TEACHER_PLAN_PRO_PIPELINE_QUOTA: int = 8
    PRIVATE_TEACHER_PLAN_BASIC_MAX_STUDENTS: int = 20
    PRIVATE_TEACHER_PLAN_PRO_MAX_STUDENTS: int = 50
    STRIPE_PRIVATE_TEACHER_PRICE_BASIC_ID: str | None = None
    STRIPE_PRIVATE_TEACHER_PRICE_PRO_ID: str | None = None
    STRIPE_STUDENT_TEACHER_ACCESS_PRICE_ID: str | None = None

    # ── Feature flags ─────────────────────────────────────────────────────────
    REVIEW_AUTO_APPROVE: bool = False

    # ── Validation ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def secrets_must_differ(self) -> Settings:
        if self.JWT_SECRET == self.ADMIN_JWT_SECRET:
            raise ValueError("JWT_SECRET and ADMIN_JWT_SECRET must be different values.")
        return self

    @field_validator("JWT_SECRET", "ADMIN_JWT_SECRET", mode="before")
    @classmethod
    def minimum_secret_length(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError(f"{info.field_name} must be at least 32 characters long.")
        return v


settings = Settings()
