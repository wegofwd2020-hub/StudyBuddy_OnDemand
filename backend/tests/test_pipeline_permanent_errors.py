"""
tests/test_pipeline_permanent_errors.py

A pipeline failure must say what went wrong, and must not retry what cannot succeed.

Both defects showed up on the same run: a Grade 8 build failed 18 of 20 units,
logging nothing but `error=anthropic call failed` — three times per content type,
54 wasted API calls — while the actual cause was an exhausted Anthropic credit
balance (HTTP 400). The provider SDK's message was destroyed by two layers of
re-wrapping, and the retry loop treated a permanent billing error as transient.
"""

from __future__ import annotations

import os
import sys

import pytest

# The pipeline package is bind-mounted at /pipeline — one level above the backend
# app root — so the repo root must be on sys.path before it can be imported. This
# is the same bootstrap test_pipeline.py performs (it does it inside each test;
# module-level imports here need it sooner).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pipeline.providers._wegofwd_adapter import (  # noqa: E402
    PermanentLLMError,
    _describe,
    _is_permanent,
    _root_cause,
)

# ── Fakes mirroring the real exception chain ──────────────────────────────────


class FakeSDKError(Exception):
    """Stands in for anthropic.BadRequestError etc."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


def _chain(outer: str, inner: Exception) -> Exception:
    """Build `LLMError("anthropic call failed") from <sdk error>`."""
    err = Exception(outer)
    err.__cause__ = inner
    return err


_CREDIT = FakeSDKError(
    "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
    "'message': 'Your credit balance is too low to access the Anthropic API.'}}"
)
_AUTH = FakeSDKError("Error code: 401 - invalid x-api-key")
_RATE_LIMIT = FakeSDKError("Error code: 429 - rate_limit_error")
_TIMEOUT = FakeSDKError("Connection timed out")


# ── The real message must survive ─────────────────────────────────────────────


def test_describe_surfaces_the_root_cause_not_the_wrapper():
    wrapped = _chain("anthropic call failed", _CREDIT)

    described = _describe(wrapped)

    # The useless wrapper text alone is not acceptable.
    assert described != "anthropic call failed"
    assert "credit balance is too low" in described


def test_root_cause_walks_the_whole_chain():
    innermost = FakeSDKError("the actual problem")
    middle = _chain("http error", innermost)
    outer = _chain("anthropic call failed", middle)

    assert _root_cause(outer) is innermost


def test_describe_is_stable_on_a_cycle():
    """A self-referencing __context__ must not hang the walk."""
    a = Exception("a")
    b = Exception("b")
    a.__cause__ = b
    b.__cause__ = a

    assert _describe(a)  # terminates


def test_describe_of_a_bare_error_is_just_its_message():
    assert _describe(FakeSDKError("plain")) == "plain"


# ── Permanent vs transient ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "sdk_error,expected",
    [
        (_CREDIT, True),  # 400 — out of credit: retrying burns money for nothing
        (_AUTH, True),  # 401 — bad key: will never authenticate
        (_RATE_LIMIT, False),  # 429 — transient by definition; retry is correct
        (_TIMEOUT, False),  # network blip — retry
    ],
    ids=["credit_400", "auth_401", "rate_limit_429", "timeout"],
)
def test_permanent_classification(sdk_error, expected):
    assert _is_permanent(_chain("anthropic call failed", sdk_error)) is expected


def test_status_code_attribute_is_preferred_over_the_message():
    """Real SDK exceptions carry status_code; don't depend on message scraping."""
    err = FakeSDKError("something opaque", status_code=403)
    assert _is_permanent(_chain("call failed", err)) is True


# ── The retry loop honours it ─────────────────────────────────────────────────


def test_permanent_error_is_a_runtime_error():
    """
    Callers that predate PermanentLLMError catch RuntimeError. Subclassing keeps
    them working unchanged — only the retry loop opts into the new behaviour.
    """
    assert issubclass(PermanentLLMError, RuntimeError)


def test_generate_with_retry_does_not_retry_a_permanent_error():
    from pipeline.build_unit import _generate_and_validate

    calls = {"n": 0}

    class Provider:
        def generate(self, prompt):
            calls["n"] += 1
            raise PermanentLLMError("anthropic call failed — credit balance is too low")

    with pytest.raises(PermanentLLMError, match="credit balance"):
        _generate_and_validate(
            provider=Provider(),
            prompt="x",
            validator=lambda d: None,
            content_type="lesson",
            max_retries=3,
        )

    assert calls["n"] == 1  # one call, not three


def test_generate_with_retry_still_retries_a_transient_error():
    from pipeline.build_unit import _generate_and_validate

    calls = {"n": 0}

    class Provider:
        def generate(self, prompt):
            calls["n"] += 1
            raise RuntimeError("anthropic call failed — 429 rate_limit_error")

    with pytest.raises(RuntimeError):
        _generate_and_validate(
            provider=Provider(),
            prompt="x",
            validator=lambda d: None,
            content_type="lesson",
            max_retries=3,
        )

    assert calls["n"] == 3
