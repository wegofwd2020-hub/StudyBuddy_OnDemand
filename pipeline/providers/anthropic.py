"""
pipeline/providers/anthropic.py

Anthropic Claude provider — wraps the existing _call_claude() pattern.

Required config attributes:
  ANTHROPIC_API_KEY  str
  CLAUDE_MODEL       str   e.g. "claude-sonnet-4-6"
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Calls Anthropic Claude via the anthropic SDK."""

    provider_id = "anthropic"

    def __init__(self, config: Any) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise RuntimeError(
                "anthropic SDK not installed. Run: pip install anthropic"
            )

        api_key = getattr(config, "ANTHROPIC_API_KEY", None)
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the anthropic provider")

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = getattr(config, "CLAUDE_MODEL", "claude-sonnet-4-6")

    def generate(self, prompt: str) -> tuple[str, int, int]:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        if not text:
            raise RuntimeError("Anthropic returned an empty response")
        input_tokens = message.usage.input_tokens if message.usage else 0
        output_tokens = message.usage.output_tokens if message.usage else 0
        return text, input_tokens, output_tokens

    @property
    def model(self) -> str:
        return self._model
