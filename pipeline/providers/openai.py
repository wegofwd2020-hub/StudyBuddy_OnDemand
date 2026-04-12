"""
pipeline/providers/openai.py

OpenAI GPT-4o provider.

Required config attributes:
  OPENAI_API_KEY   str
  OPENAI_MODEL     str   default "gpt-4o"  (pinned — never "latest")

JSON reliability: GPT-4o with response_format={"type": "json_object"} is
highly reliable for structured output. The existing 3× retry + validation
loop in build_unit handles any remaining failures.

Note: Prompt variants tuned for Claude's instruction-following characteristics
may need iterative refinement when running GPT-4o. Per the design doc, prompt
parity work is a separate workstream from this abstraction layer.
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Calls OpenAI GPT-4o via the openai SDK."""

    provider_id = "openai"

    def __init__(self, config: Any) -> None:
        try:
            import openai  # type: ignore
        except ImportError:
            raise RuntimeError(
                "openai SDK not installed. Run: pip install openai"
            )

        api_key = getattr(config, "OPENAI_API_KEY", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the openai provider")

        self._client = openai.OpenAI(api_key=api_key)
        self._model = getattr(config, "OPENAI_MODEL", "gpt-4o")

    def generate(self, prompt: str) -> tuple[str, int, int]:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=8192,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        choice = response.choices[0] if response.choices else None
        text = choice.message.content if choice and choice.message else ""
        if not text:
            raise RuntimeError("OpenAI returned an empty response")
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        return text, input_tokens, output_tokens

    @property
    def model(self) -> str:
        return self._model
