"""Social login integration tests (verifier monkeypatched → hermetic)."""

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from app.auth import social
from app.auth.social import SocialIdentity, SocialProvider
from app.core.redis_client import get_redis

pytestmark = pytest.mark.integration


def _fake_verifier(identity: SocialIdentity) -> Callable[..., Awaitable[SocialIdentity]]:
    async def _verify(_provider: SocialProvider, _id_token: str) -> SocialIdentity:
        return identity

    return _verify


def _me(api: AsyncClient, tokens: dict[str, str]) -> Awaitable:
    return api.get("/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})


@pytest.mark.req("A-1", "A-3")
async def test_social_login_creates_then_reuses_user(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = SocialIdentity(SocialProvider.GOOGLE, "google-sub-1", "ana@gmail.com", "Ana G")
    monkeypatch.setattr(social, "verify_token", _fake_verifier(identity))

    first = await api.post("/api/v1/auth/social", json={"provider": "google", "id_token": "x"})
    assert first.status_code == 200, first.text
    tokens = first.json()
    me1 = (await _me(api, tokens)).json()
    assert me1["email"] == "ana@gmail.com"
    assert me1["role"] == "client"
    # New social accounts start incomplete (missing document/birth_date/gender).
    assert me1["status"] == "profile_incomplete"

    # Auth-required business endpoints are blocked until the profile is completed.
    patched = await api.patch(
        "/api/v1/me",
        json={"first_name": "X"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert patched.status_code == 403
    assert patched.json()["error"]["code"] == "profile_incomplete"

    # Completing the profile activates the account.
    completed = await api.post(
        "/api/v1/me/complete-profile",
        json={
            "document_type": "CC",
            "document_number": "1032456789",
            "gender": "female",
            "birth_date": "1996-04-12",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "active"
    assert completed.json()["document_number"] == "1032456789"

    # same provider subject → same account
    second = await api.post("/api/v1/auth/social", json={"provider": "google", "id_token": "y"})
    me2 = (await _me(api, second.json())).json()
    assert me2["id"] == me1["id"]
    assert me2["status"] == "active"  # stays active on re-login


@pytest.mark.req("A-1")
async def test_social_login_links_existing_email(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    phone = "+573150000010"
    await api.post(
        "/api/v1/auth/register",
        json={
            "role": "client",
            "first_name": "Beto",
            "last_name": "Pérez",
            "document_type": "CC",
            "document_number": phone.lstrip("+"),
            "phone": phone,
            "email": "beto@x.com",
            "password": "supersecret",
            "gender": "male",
            "birth_date": "1990-01-01",
            "accept_habeas_data": True,
        },
    )
    code = await get_redis().get(f"otp:{phone}")
    verify = await api.post("/api/v1/auth/verify-otp", json={"phone": phone, "code": code})
    existing_id = (await _me(api, verify.json())).json()["id"]

    identity = SocialIdentity(SocialProvider.GOOGLE, "google-sub-2", "beto@x.com", "Beto")
    monkeypatch.setattr(social, "verify_token", _fake_verifier(identity))
    social_resp = await api.post(
        "/api/v1/auth/social", json={"provider": "google", "id_token": "z"}
    )
    linked_id = (await _me(api, social_resp.json())).json()["id"]

    assert linked_id == existing_id  # linked to the same account


@pytest.mark.req("A-1")
async def test_social_login_provider_not_configured(api: AsyncClient) -> None:
    # No GOOGLE_CLIENT_ID in the test env → the real verifier reports not configured.
    resp = await api.post("/api/v1/auth/social", json={"provider": "google", "id_token": "x"})
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "provider_not_configured"
