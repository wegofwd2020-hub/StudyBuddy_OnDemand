"""
pipeline/config.py

All pipeline configuration via pydantic-settings.
Required env vars fail fast if missing.
"""

from __future__ import annotations

import sys
import os
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Pull AI cost defaults from the shared pricing module.
# Add backend/ to sys.path so pipeline scripts can import src.pricing.
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend_dir))

from src.pricing import AI_COST as _ai  # noqa: E402


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

    # ── LLM Provider selection ────────────────────────────────────────────────
    # Default provider used by build_unit / build_grade when --provider is not given.
    # Valid values: "anthropic" | "openai" | "google"
    DEFAULT_PROVIDER: str = "anthropic"

    # ── Model pins (never implicit "latest") ─────────────────────────────────
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # ── Provider API keys (optional — only required when provider is selected) ─
    # ANTHROPIC_API_KEY is already required above (it's the default provider).
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # ── TTS ───────────────────────────────────────────────────────────────────
    TTS_PROVIDER: Optional[str] = None   # "polly" | "google" | None
    TTS_API_KEY: Optional[str] = None    # used for Google TTS

    # ── Cost controls ─────────────────────────────────────────────────────────
    # Defaults sourced from backend/src/pricing.py (AI_COST).
    # Override via env var only when testing with a different model.
    MAX_PIPELINE_COST_USD: float = _ai.max_run_usd.__float__()
    TOKEN_COST_INPUT_USD: float  = _ai.input_per_token_usd    # $3 / 1M input tokens
    TOKEN_COST_OUTPUT_USD: float = _ai.output_per_token_usd   # $15 / 1M output tokens

    # ── Database (for seed_default / build_grade upserts) ─────────────────────
    DATABASE_URL: Optional[str] = None

    # ── Review ────────────────────────────────────────────────────────────────
    REVIEW_AUTO_APPROVE: bool = False

    # ── Content version (target version for idempotency check) ───────────────
    CONTENT_VERSION: int = 1

    # ── AWS / CDN ─────────────────────────────────────────────────────────────
    # If set, built content is uploaded to S3 after local write.
    S3_BUCKET_NAME: Optional[str] = None

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
