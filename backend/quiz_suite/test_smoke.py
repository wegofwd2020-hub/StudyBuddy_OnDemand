"""Proves the suite can reach the live app before any other tier is trusted."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.quiz_live


@pytest.mark.asyncio
async def test_live_app_is_reachable(api):
    r = await api.get("/healthz")
    assert r.status_code == 200, f"live stack not reachable: {r.status_code}"
