"""Error-handling and request-context tests (F-5)."""

import pytest
from httpx import AsyncClient


@pytest.mark.req("F-5")
async def test_not_found_uses_standard_error_shape(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "http_404"
    assert "message" in body["error"]


@pytest.mark.req("F-5")
async def test_request_id_header_present(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.headers.get("x-request-id")


@pytest.mark.req("F-5")
async def test_request_id_is_propagated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert resp.headers.get("x-request-id") == "abc-123"
