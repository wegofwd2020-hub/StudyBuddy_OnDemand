"""
pipeline/config.py

All pipeline configuration via pydantic-settings.
Required env vars fail fast if missing.
"""

from __future__ import annotations

from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str
    CONTENT_STORE_PATH: str

    # ── Model (pinned — never implicit latest) ────────────────────────────────
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # ── TTS ───────────────────────────────────────────────────────────────────
    TTS_PROVIDER: Optional[str] = None   # "polly" | "google" | None
    TTS_API_KEY: Optional[str] = None    # used for Google TTS

    # ── Cost controls ─────────────────────────────────────────────────────────
    MAX_PIPELINE_COST_USD: float = 50.0
    # Rough per-token cost estimates (USD)
    TOKEN_COST_INPUT_USD: float = 0.000003   # $3 / 1M input tokens
    TOKEN_COST_OUTPUT_USD: float = 0.000015  # $15 / 1M output tokens

    # ── Database (for seed_default / build_grade upserts) ─────────────────────
    DATABASE_URL: Optional[str] = None

    # ── Review ────────────────────────────────────────────────────────────────
    REVIEW_AUTO_APPROVE: bool = False

    # ── Content version (target version for idempotency check) ───────────────
    CONTENT_VERSION: int = 1

    # ── Observability ─────────────────────────────────────────────────────────
    # If set, pipeline run metrics are pushed to this Pushgateway URL on completion.
    # e.g. "http://pushgateway:9091"
    PUSHGATEWAY_URL: Optional[str] = None

    @model_validator(mode="after")
    def required_fields_present(self) -> "PipelineSettings":
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not self.CONTENT_STORE_PATH:
            raise ValueError("CONTENT_STORE_PATH is required")
        return self


settings = PipelineSettings()
