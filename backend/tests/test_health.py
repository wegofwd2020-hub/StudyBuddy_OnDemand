"""
tests/test_health.py

Tests for GET /health endpoint.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    """Health endpoint returns 200 with db and redis ok when dependencies are up."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["db"] == "ok"
    assert data["redis"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_has_correlation_id(client: AsyncClient):
    """Every response includes X-Correlation-Id header."""
    response = await client.get("/health")
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_health_with_provided_correlation_id(client: AsyncClient):
    """If X-Correlation-Id is sent by caller, it is echoed back."""
    custom_cid = "test-correlation-id-12345"
    response = await client.get("/health", headers={"X-Correlation-Id": custom_cid})
    assert response.headers.get("x-correlation-id") == custom_cid


@pytest.mark.asyncio
async def test_metrics_requires_token(client: AsyncClient):
    """GET /metrics without a valid token returns 403."""
    response = await client.get("/metrics")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_metrics_with_valid_token(client: AsyncClient):
    """GET /metrics with valid METRICS_TOKEN returns Prometheus text."""
    response = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer test-metrics-token"},
    )
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
