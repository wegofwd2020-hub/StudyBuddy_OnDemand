"""
pipeline/providers/registry.py

Maps provider_id strings to provider instances, resolved from config.

Supported provider IDs:
  "anthropic"  — Anthropic Claude (default)   — via the shared wegofwd-llm package
  "openai"     — OpenAI GPT-4o                 — via the shared wegofwd-llm package
  "google"     — Google Gemini (2.5-flash)     — via wegofwd-llm's "gemini" (OpenAI-compat)

All three providers are backed by **wegofwd-llm** (StudyBuddy_SelfLearner ADR-012 —
one source of truth for the vendor call + provider registry across the product
family); a thin adapter (``_wegofwd_adapter.WegofwdAdapter``) preserves the legacy
``generate(prompt) -> (text, in, out)`` interface, so every call site is unchanged.
``google`` maps to wegofwd-llm's ``gemini`` provider (the OpenAI-compatible Gemini
endpoint), verified live 2026-06-09.

Each provider reads its own API key from config. If the key is missing,
instantiation raises RuntimeError immediately — fail fast.
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider

# OnDemand provider_id -> (wegofwd-llm provider id, config key attr,
# config model attr, model default, response_format passed to the seam to
# mirror the old provider). The wegofwd id differs only for google ("gemini").
_WEGOFWD_PROVIDERS: dict[str, tuple[str, str, str, str, str | None]] = {
    # anthropic: the old provider used a plain messages call (no JSON mode).
    "anthropic": ("anthropic", "ANTHROPIC_API_KEY", "CLAUDE_MODEL", "claude-sonnet-4-6", None),
    # openai: the old provider hard-coded response_format={"type":"json_object"}.
    "openai": ("openai", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o", "json"),
    # google -> wegofwd "gemini" (OpenAI-compat endpoint). The old GeminiProvider
    # set response_mime_type="application/json" + max_output_tokens=8192; "json"
    # mode + the gemini Capabilities cap (8192) mirror that. 1.5-pro is retired —
    # default to the verified gemini-2.5-flash.
    "google": ("gemini", "GOOGLE_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash", "json"),
}

_VALID = sorted(_WEGOFWD_PROVIDERS)


def get_provider(provider_id: str, config: Any) -> LLMProvider:
    """
    Instantiate and return the named provider.

    Args:
        provider_id: One of "anthropic", "openai", "google".
        config:      PipelineSettings instance (or any object with the required
                     API key / model attributes).

    Raises:
        ValueError:    Unknown provider_id.
        RuntimeError:  Missing SDK or API key.
    """
    if provider_id in _WEGOFWD_PROVIDERS:
        wegofwd_id, key_attr, model_attr, model_default, response_format = _WEGOFWD_PROVIDERS[
            provider_id
        ]
        api_key = getattr(config, key_attr, None)
        if not api_key:
            raise RuntimeError(f"{key_attr} is required for the {provider_id} provider")
        from pipeline.providers._wegofwd_adapter import WegofwdAdapter

        return WegofwdAdapter(
            provider_id=provider_id,
            wegofwd_id=wegofwd_id,
            api_key=api_key,
            model=getattr(config, model_attr, model_default),
            response_format=response_format,
        )

    raise ValueError(f"Unknown provider '{provider_id}'. Valid options: {', '.join(_VALID)}")


def list_providers() -> list[str]:
    """Return sorted list of registered provider IDs."""
    return list(_VALID)
