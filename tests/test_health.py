"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.req("F-1")
async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "BarriApp"
