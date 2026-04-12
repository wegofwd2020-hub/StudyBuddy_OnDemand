"""
pipeline/providers/registry.py

Maps provider_id strings to provider classes and resolves instances from config.

Supported provider IDs:
  "anthropic"  — Anthropic Claude (default)
  "openai"     — OpenAI GPT-4o
  "google"     — Google Gemini 1.5 Pro

Each provider reads its own API key from config. If the key is missing or the
SDK is not installed, instantiation raises RuntimeError immediately — fail fast.
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider

_REGISTRY: dict[str, type[LLMProvider]] = {}


def _register() -> None:
    """Lazily populate registry on first call."""
    if _REGISTRY:
        return
    from pipeline.providers.anthropic import AnthropicProvider
    from pipeline.providers.openai import OpenAIProvider
    from pipeline.providers.google import GeminiProvider

    _REGISTRY["anthropic"] = AnthropicProvider
    _REGISTRY["openai"] = OpenAIProvider
    _REGISTRY["google"] = GeminiProvider


def get_provider(provider_id: str, config: Any) -> LLMProvider:
    """
    Instantiate and return the named provider.

    Args:
        provider_id: One of "anthropic", "openai", "google".
        config:      PipelineSettings instance (or any object with the
                     required API key attributes).

    Raises:
        ValueError:    Unknown provider_id.
        RuntimeError:  Missing SDK or API key.
    """
    _register()
    cls = _REGISTRY.get(provider_id)
    if cls is None:
        valid = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown provider '{provider_id}'. Valid options: {valid}"
        )
    return cls(config)


def list_providers() -> list[str]:
    """Return sorted list of registered provider IDs."""
    _register()
    return sorted(_REGISTRY)
