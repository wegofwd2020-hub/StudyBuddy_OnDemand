"""
pipeline/providers/_wegofwd_adapter.py

Adapts a ``wegofwd_llm.Provider`` to this pipeline's legacy ``LLMProvider``
tuple interface (``generate(prompt) -> (text, input_tokens, output_tokens)``),
so the multi-provider engine is consolidated onto the shared ``wegofwd-llm``
package (StudyBuddy_SelfLearner ADR-012 — one source of truth, no 3-way drift)
**without changing a single call site**.

Behaviour parity with the providers it replaces:
- ``anthropic`` → ``response_format=None`` → a plain ``messages.create`` (the old
  AnthropicProvider's prompt-embedded-JSON call). ``max_tokens`` is the contract
  default 16384 — the same value the old provider hard-coded.
- ``openai`` → ``response_format="json"`` → ``{"type": "json_object"}`` (what the
  old OpenAIProvider hard-coded), again at 16384.

Errors are remapped to ``RuntimeError`` to preserve the legacy provider contract
(``base.py``: "Raises RuntimeError on API errors / empty responses"). The
wegofwd-llm message is key-free by guarantee, so re-raising its text is safe.
"""

from __future__ import annotations

from pipeline.providers.base import LLMProvider


class WegofwdAdapter(LLMProvider):
    """A legacy-interface ``LLMProvider`` backed by a ``wegofwd_llm.Provider``."""

    def __init__(
        self,
        *,
        provider_id: str,
        api_key: str,
        model: str,
        response_format: str | None,
    ) -> None:
        # Imported lazily so importing the registry doesn't require the package
        # for the google-only path.
        from wegofwd_llm import LLMError, build_provider

        self.provider_id = provider_id
        self._model = model
        self._response_format = response_format
        try:
            self._inner = build_provider(provider_id, api_key=api_key, model=model)
        except LLMError as exc:
            # Legacy contract: a missing SDK / bad config is a RuntimeError.
            raise RuntimeError(str(exc)) from exc

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str) -> tuple[str, int, int]:
        from wegofwd_llm import LLMError, LLMRequest

        try:
            resp = self._inner.generate(
                LLMRequest(prompt=prompt, response_format=self._response_format)
            )
        except LLMError as exc:
            # Preserve the legacy contract: providers raise RuntimeError on failure.
            raise RuntimeError(str(exc)) from exc
        if not resp.text:
            raise RuntimeError(f"{provider_label(self.provider_id)} returned an empty response")
        return resp.text, resp.input_tokens, resp.output_tokens


def provider_label(provider_id: str) -> str:
    """Human label used in the empty-response error, matching the old messages."""
    return {"anthropic": "Anthropic", "openai": "OpenAI"}.get(provider_id, provider_id)
