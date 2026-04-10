"""
backend/src/core/stripe_async.py

Async wrapper for the synchronous Stripe Python SDK.

stripe-python uses blocking HTTP (httpx/requests) calls.  Calling the SDK
directly inside an async FastAPI handler blocks the entire event loop for
the duration of the round-trip (~200-800ms), preventing all other requests
from being served.

Usage:
    from src.core.stripe_async import run_stripe

    # Before (blocks event loop):
    session = stripe.checkout.Session.create(**params)

    # After (non-blocking):
    session = await run_stripe(stripe.checkout.Session.create, **params)

run_stripe() works with any stripe SDK callable — positional args, keyword
args, and mixed signatures are all handled correctly via functools.partial.
Exceptions raised by the SDK propagate through the awaitable unchanged, so
existing try/except blocks need no changes.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any


async def run_stripe(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """
    Run a synchronous Stripe SDK call in the default thread pool executor.

    Keeps the asyncio event loop unblocked while Stripe's blocking HTTP
    call completes in a background thread.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))
