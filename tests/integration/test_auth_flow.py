"""End-to-end auth flow: register -> verify OTP -> /me -> login (integration)."""

import pytest
from httpx import AsyncClient

from app.core.redis_client import get_redis

pytestmark = pytest.mark.integration


async def _register_and_verify(api: AsyncClient, phone: str, password: str) -> dict[str, str]:
    resp = await api.post(
        "/api/v1/auth/register",
        json={
            "role": "client",
            "first_name": "Ana",
            "last_name": "Test",
            "document_type": "CC",
            "document_number": phone.lstrip("+"),
            "phone": phone,
            "email": f"{phone.lstrip('+')}@barriapp.co",
            "password": password,
            "gender": "female",
            "birth_date": "1990-01-01",
            "accept_habeas_data": True,
        },
    )
    assert resp.status_code == 201, resp.text

    code = await get_redis().get(f"otp:{phone}")
    assert code is not None

    resp = await api.post("/api/v1/auth/verify-otp", json={"phone": phone, "code": code})
    assert resp.status_code == 200, resp.text
    tokens: dict[str, str] = resp.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    return tokens


@pytest.mark.req("A-1", "A-2", "A-3")
async def test_register_verify_and_get_profile(api: AsyncClient) -> None:
    phone = "+573001112233"
    tokens = await _register_and_verify(api, phone, "supersecret")

    resp = await api.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["phone"] == phone
    assert body["status"] == "active"
    assert body["role"] == "client"


@pytest.mark.req("A-3")
async def test_login_with_wrong_password_is_rejected(api: AsyncClient) -> None:
    phone = "+573004445566"
    await _register_and_verify(api, phone, "supersecret")

    resp = await api.post("/api/v1/auth/login", json={"phone": phone, "password": "wrong-pass"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.req("A-5")
async def test_me_requires_authentication(api: AsyncClient) -> None:
    resp = await api.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


@pytest.mark.req("A-3")
async def test_refresh_issues_new_tokens(api: AsyncClient) -> None:
    phone = "+573007778899"
    tokens = await _register_and_verify(api, phone, "supersecret")

    resp = await api.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
