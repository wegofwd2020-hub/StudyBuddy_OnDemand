"""
mobile/src/api/subscription_client.py

Async HTTP client for subscription and payment endpoints.

Layer rule: this module is in the api layer — only calls backend REST.
Never calls Stripe directly. Never holds Stripe keys.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

try:
    from mobile.config import BACKEND_URL  # type: ignore
except ImportError:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def get_subscription_status(token: str) -> dict:
    """
    Fetch the student's current subscription status.

    Returns: {plan, status, valid_until, lessons_accessed, stripe_subscription_id}
    plan is "free", "monthly", or "annual".
    status is "active", "cancelled", "past_due", or "free".
    """
    url = f"{BACKEND_URL}/api/v1/subscription/status"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()


async def get_checkout_url(
    token: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session and return the hosted checkout URL.

    The caller opens this URL in a system browser or WebView.
    Returns the checkout_url string.
    """
    url = f"{BACKEND_URL}/api/v1/subscription/checkout"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            json={
                "plan": plan,
                "success_url": success_url,
                "cancel_url": cancel_url,
            },
            headers=_auth_headers(token),
        )
        response.raise_for_status()
        return response.json()["checkout_url"]


async def cancel_subscription(token: str) -> dict:
    """
    Cancel the student's subscription at the end of the current billing period.

    Returns: {status, current_period_end}
    status will be "cancelled_at_period_end".
    """
    url = f"{BACKEND_URL}/api/v1/subscription"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(url, headers=_auth_headers(token))
        response.raise_for_status()
        return response.json()
