"""
pipeline/providers/registry.py

Maps provider_id strings to provider instances, resolved from config.

Supported provider IDs:
  "anthropic"  — Anthropic Claude (default)   — via the shared wegofwd-llm package
  "openai"     — OpenAI GPT-4o                 — via the shared wegofwd-llm package
  "google"     — Google Gemini 1.5 Pro         — native Google SDK (pipeline-local)

``anthropic`` and ``openai`` are backed by **wegofwd-llm** (StudyBuddy_SelfLearner
ADR-012 — one source of truth for the vendor call + provider registry across the
product family); a thin adapter (``_wegofwd_adapter.WegofwdAdapter``) preserves the
legacy ``generate(prompt) -> (text, in, out)`` interface, so every call site is
unchanged. ``google`` keeps its native ``GeminiProvider`` until the OpenAI-compatible
Gemini path is live-verified (it is a different transport + model availability).

Each provider reads its own API key from config. If the key is missing or the SDK
is not installed, instantiation raises RuntimeError immediately — fail fast.
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider

# OnDemand provider_id -> (config key attr, config model attr, model default,
# response_format passed to the wegofwd-llm seam to mirror the old provider).
_WEGOFWD_PROVIDERS: dict[str, tuple[str, str, str, str | None]] = {
    # anthropic: the old provider used a plain messages call (no JSON mode).
    "anthropic": ("ANTHROPIC_API_KEY", "CLAUDE_MODEL", "claude-sonnet-4-6", None),
    # openai: the old provider hard-coded response_format={"type":"json_object"}.
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o", "json"),
}

_VALID = sorted({"google", *_WEGOFWD_PROVIDERS})


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
        key_attr, model_attr, model_default, response_format = _WEGOFWD_PROVIDERS[provider_id]
        api_key = getattr(config, key_attr, None)
        if not api_key:
            raise RuntimeError(f"{key_attr} is required for the {provider_id} provider")
        from pipeline.providers._wegofwd_adapter import WegofwdAdapter

        return WegofwdAdapter(
            provider_id=provider_id,
            api_key=api_key,
            model=getattr(config, model_attr, model_default),
            response_format=response_format,
        )

    if provider_id == "google":
        from pipeline.providers.google import GeminiProvider

        return GeminiProvider(config)

    raise ValueError(f"Unknown provider '{provider_id}'. Valid options: {', '.join(_VALID)}")


def list_providers() -> list[str]:
    """Return sorted list of registered provider IDs."""
    return list(_VALID)
