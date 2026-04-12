"""
pipeline/providers/google.py

Google Gemini provider via the google-generativeai SDK.

Required config attributes:
  GOOGLE_API_KEY   str
  GEMINI_MODEL     str   default "gemini-1.5-pro"  (pinned — never "latest")

JSON reliability: Gemini 1.5 Pro has good structured output support but may
occasionally include markdown fences despite instructions. The shared
_parse_json_response() in build_unit strips fences before validation, and
the 3× retry loop handles any remaining failures.
"""

from __future__ import annotations

from typing import Any

from pipeline.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Calls Google Gemini via the google-generativeai SDK."""

    provider_id = "google"

    def __init__(self, config: Any) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            raise RuntimeError(
                "google-generativeai SDK not installed. "
                "Run: pip install google-generativeai"
            )

        api_key = getattr(config, "GOOGLE_API_KEY", None)
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for the google provider")

        genai.configure(api_key=api_key)
        model_name = getattr(config, "GEMINI_MODEL", "gemini-1.5-pro")
        self._model_name = model_name
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": 8192,
            },
        )

    def generate(self, prompt: str) -> tuple[str, int, int]:
        response = self._model.generate_content(prompt)
        text = response.text if response.text else ""
        if not text:
            raise RuntimeError("Gemini returned an empty response")

        # google-generativeai SDK exposes usage_metadata on the response
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        return text, input_tokens, output_tokens

    @property
    def model(self) -> str:
        return self._model_name
