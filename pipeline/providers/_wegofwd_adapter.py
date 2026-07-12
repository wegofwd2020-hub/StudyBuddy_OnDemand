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
- ``google`` → ``response_format="json"`` → the wegofwd-llm gemini provider
  (OpenAI-compatible endpoint), mirroring the old GeminiProvider's
  ``response_mime_type="application/json"``. ``wegofwd_id`` is ``"gemini"`` — the
  pipeline's provider_id stays ``"google"`` for call-site/audit consistency.
  Output is capped at 8192 by the gemini Capabilities, matching the old provider.

Errors are remapped to ``RuntimeError`` to preserve the legacy provider contract
(``base.py``: "Raises RuntimeError on API errors / empty responses"). The
wegofwd-llm message is key-free by guarantee, so re-raising its text is safe.
"""

from __future__ import annotations

import re

from pipeline.providers.base import LLMProvider


class PermanentLLMError(RuntimeError):
    """
    An LLM failure that retrying cannot fix.

    Exhausted credits, a bad API key, a disabled model: the call will fail
    identically every time. The build loop retries ``RuntimeError`` three times,
    which for these turns one wasted call into three and buries the real message
    under "Failed after 3 attempts".
    """


# HTTP statuses that will never succeed on retry, however many times we ask.
# 429 is deliberately NOT here — rate limits are transient and worth retrying.
_PERMANENT_STATUSES = (400, 401, 403, 404)


def _root_cause(exc: BaseException) -> BaseException:
    """Walk to the deepest cause — where the provider SDK's real message lives."""
    seen: set[int] = set()
    cur = exc
    while True:
        nxt = cur.__cause__ or cur.__context__
        if nxt is None or id(nxt) in seen:
            return cur
        seen.add(id(nxt))
        cur = nxt


def _describe(exc: BaseException) -> str:
    """
    Build a message that says what actually went wrong.

    ``wegofwd_llm`` raises ``LLMError("anthropic call failed")`` — true but
    useless. The provider SDK's exception (e.g. anthropic's
    "Your credit balance is too low") is one or two links down the ``__cause__``
    chain, and was being thrown away. An 18-unit build once failed with nothing
    but "anthropic call failed" ×54 when the account had simply run out of credit.
    """
    root = _root_cause(exc)
    if root is exc:
        return str(exc)
    return f"{exc} — {type(root).__name__}: {root}"


def _is_permanent(exc: BaseException) -> bool:
    root = _root_cause(exc)
    status = getattr(root, "status_code", None)
    if status is None:
        # anthropic/openai SDK errors carry the code in the text as "Error code: NNN".
        m = re.search(r"Error code:\s*(\d{3})", str(root))
        status = int(m.group(1)) if m else None
    return status in _PERMANENT_STATUSES


class WegofwdAdapter(LLMProvider):
    """A legacy-interface ``LLMProvider`` backed by a ``wegofwd_llm.Provider``."""

    def __init__(
        self,
        *,
        provider_id: str,
        wegofwd_id: str,
        api_key: str,
        model: str,
        response_format: str | None,
    ) -> None:
        # Imported lazily so importing the registry doesn't require the package.
        from wegofwd_llm import LLMError, build_provider

        # provider_id is the pipeline-facing id (e.g. "google"); wegofwd_id is the
        # package's id for the same vendor (e.g. "gemini").
        self.provider_id = provider_id
        self._model = model
        self._response_format = response_format
        try:
            self._inner = build_provider(wegofwd_id, api_key=api_key, model=model)
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
            # PermanentLLMError is a RuntimeError, so callers that don't know about
            # it behave exactly as before; the retry loop checks for it and stops.
            error_class = PermanentLLMError if _is_permanent(exc) else RuntimeError
            raise error_class(_describe(exc)) from exc
        if not resp.text:
            raise RuntimeError(f"{provider_label(self.provider_id)} returned an empty response")
        return resp.text, resp.input_tokens, resp.output_tokens


def provider_label(provider_id: str) -> str:
    """Human label used in the empty-response error, matching the old messages."""
    return {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Gemini"}.get(
        provider_id, provider_id
    )
