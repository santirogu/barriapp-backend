"""Hardening integration tests: security headers + login rate limiting."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration


@pytest.mark.req("A-5")
async def test_security_headers_present(api: AsyncClient) -> None:
    resp = await api.get("/api/v1/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "no-referrer"


@pytest.mark.req("A-5")
async def test_login_is_rate_limited(api: AsyncClient, register_user: RegisterUser) -> None:
    phone = "+573140000001"
    await register_user(phone)  # active user, password "supersecret"

    statuses = []
    for _ in range(11):  # limit is 10 per window
        resp = await api.post(
            "/api/v1/auth/login", json={"phone": phone, "password": "supersecret"}
        )
        statuses.append(resp.status_code)

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429

    blocked = await api.post("/api/v1/auth/login", json={"phone": phone, "password": "supersecret"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
