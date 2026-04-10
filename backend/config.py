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

    # ── Connection pool arithmetic ────────────────────────────────────────────
    # Total connections to PgBouncer = DATABASE_POOL_MAX × WORKER_COUNT.
    # This must not exceed PGBOUNCER_POOL_SIZE or connections will be queued
    # or dropped under load, producing intermittent asyncpg.TooManyConnectionsError.
    #
    # Default WORKER_COUNT=1 matches single-worker dev; set it to the gunicorn
    # worker count (-w N) in production.  Default PGBOUNCER_POOL_SIZE=100 is the
    # recommended PgBouncer pool size for a 4-worker deployment with pool_max=20.
    PGBOUNCER_POOL_SIZE: int = 100
    WORKER_COUNT: int = 1

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
    # "local" uses CONTENT_STORE_PATH on the local filesystem (default, single-host).
    # "s3" uses S3_BUCKET_NAME + S3_KEY_PREFIX (multi-host production).
    STORAGE_BACKEND: str = "local"
    S3_KEY_PREFIX: str = ""  # optional path prefix within the bucket

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
    # Pricing defaults come from src/pricing.py — only Stripe IDs live here.
    STRIPE_SCHOOL_PRICE_STARTER_ID: str | None = None
    STRIPE_SCHOOL_PRICE_PROFESSIONAL_ID: str | None = None
    STRIPE_SCHOOL_PRICE_ENTERPRISE_ID: str | None = None

    # ── Retention billing — one-time payment price IDs ────────────────────────
    # Set these in .env; leave None in dev (endpoints return 503 when unset).
    STRIPE_SCHOOL_PRICE_RENEWAL_ID: str | None = None        # per-curriculum renewal
    STRIPE_SCHOOL_PRICE_STORAGE_5GB_ID: str | None = None    # +5 GB storage add-on
    STRIPE_SCHOOL_PRICE_STORAGE_10GB_ID: str | None = None   # +10 GB storage add-on
    STRIPE_SCHOOL_PRICE_STORAGE_25GB_ID: str | None = None   # +25 GB storage add-on

    # ── School seat limits by plan ────────────────────────────────────────────
    # Defaults sourced from src/pricing.py — override via env var for unusual deploys.
    @property
    def school_seats_starter_students(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["starter"].max_students

    @property
    def school_seats_starter_teachers(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["starter"].max_teachers

    @property
    def school_seats_professional_students(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["professional"].max_students

    @property
    def school_seats_professional_teachers(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["professional"].max_teachers

    @property
    def school_seats_enterprise_students(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["enterprise"].max_students

    @property
    def school_seats_enterprise_teachers(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["enterprise"].max_teachers

    # ── School curriculum build allowance per plan ────────────────────────────
    # Defaults sourced from src/pricing.py. -1 = unlimited (Enterprise).
    @property
    def school_builds_starter(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["starter"].builds_per_year

    @property
    def school_builds_professional(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["professional"].builds_per_year

    @property
    def school_builds_enterprise(self) -> int:
        from src.pricing import SCHOOL_PLANS
        return SCHOOL_PLANS["enterprise"].builds_per_year

    # ── Independent teacher plan pricing ─────────────────────────────────────
    # Defaults sourced from src/pricing.py — future: teacher tier rebuild (#57).
    @property
    def teacher_plan_solo_monthly_usd(self) -> str:
        from src.pricing import TEACHER_PLANS
        return next(p.price_monthly for p in TEACHER_PLANS if p.id == "solo")

    @property
    def teacher_plan_growth_monthly_usd(self) -> str:
        from src.pricing import TEACHER_PLANS
        return next(p.price_monthly for p in TEACHER_PLANS if p.id == "growth")

    @property
    def teacher_plan_pro_monthly_usd(self) -> str:
        from src.pricing import TEACHER_PLANS
        return next(p.price_monthly for p in TEACHER_PLANS if p.id == "pro")

    # ── School curriculum build allowance per plan (Option A — absorbed into plan)
    # Number of grade-level pipeline builds included per subscription year.
    # -1 = unlimited (Enterprise).
    SCHOOL_BUILDS_STARTER: int = 1
    SCHOOL_BUILDS_PROFESSIONAL: int = 3
    SCHOOL_BUILDS_ENTERPRISE: int = -1  # unlimited

    # ── Extra curriculum build — pay-per-build (Option B, #106) ──────────────
    # One-time $15 Stripe payment per grade beyond plan allowance.
    STRIPE_SCHOOL_PRICE_EXTRA_BUILD_ID: str | None = None

    # ── Credit bundles — rollover build credits (Option C, #107) ─────────────
    # One-time Stripe payments; credits never expire.
    # Bundles: 3 credits/$39  ·  10 credits/$119  ·  25 credits/$269
    STRIPE_SCHOOL_PRICE_CREDITS_3_ID: str | None = None
    STRIPE_SCHOOL_PRICE_CREDITS_10_ID: str | None = None
    STRIPE_SCHOOL_PRICE_CREDITS_25_ID: str | None = None

    # ── Independent Teacher plan pricing (Option A — flat fee, teacher keeps student revenue)
    # Future: Option B (revenue share) tracked in feat/q2-b-revenue-share.
    #         Option C (seat-tiered flat) tracked in feat/q2-c-seat-tiered.
    TEACHER_PLAN_SOLO_MONTHLY_USD: str = "29.00"   # Solo: up to 25 students
    TEACHER_PLAN_GROWTH_MONTHLY_USD: str = "59.00"  # Growth: up to 75 students (future)
    TEACHER_PLAN_PRO_MONTHLY_USD: str = "99.00"     # Pro: up to 200 students (future)

    # ── Feature flags ─────────────────────────────────────────────────────────
    REVIEW_AUTO_APPROVE: bool = False

    # ── Validation ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def secrets_must_differ(self) -> Settings:
        if self.JWT_SECRET == self.ADMIN_JWT_SECRET:
            raise ValueError("JWT_SECRET and ADMIN_JWT_SECRET must be different values.")
        return self

    @model_validator(mode="after")
    def connection_pool_arithmetic(self) -> Settings:
        """
        Guard against pool exhaustion before the first connection is made.

        Total connections = DATABASE_POOL_MAX × WORKER_COUNT must not exceed
        PGBOUNCER_POOL_SIZE.  A violation here surfaces at startup (config
        import) rather than as intermittent asyncpg.TooManyConnectionsError
        under production load.
        """
        total = self.DATABASE_POOL_MAX * self.WORKER_COUNT
        if total > self.PGBOUNCER_POOL_SIZE:
            raise ValueError(
                f"Connection pool arithmetic invalid: "
                f"DATABASE_POOL_MAX ({self.DATABASE_POOL_MAX}) × "
                f"WORKER_COUNT ({self.WORKER_COUNT}) = {total} connections "
                f"> PGBOUNCER_POOL_SIZE ({self.PGBOUNCER_POOL_SIZE}). "
                f"Reduce DATABASE_POOL_MAX, increase PGBOUNCER_POOL_SIZE, "
                f"or reduce WORKER_COUNT."
            )
        return self

    @field_validator("JWT_SECRET", "ADMIN_JWT_SECRET", mode="before")
    @classmethod
    def minimum_secret_length(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError(f"{info.field_name} must be at least 32 characters long.")
        return v


settings = Settings()
