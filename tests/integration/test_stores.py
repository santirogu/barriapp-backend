"""Stores integration tests: onboarding, geo search, ownership (S-1, S-4)."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _store_payload(name: str, coords: list[float]) -> dict[str, object]:
    return {
        "name": name,
        "location": {"line": "Cra 10 #20-30", "geo": {"type": "Point", "coordinates": coords}},
    }


@pytest.mark.req("S-1", "S-4", "U-4")
async def test_create_store_grants_seller_and_is_geo_searchable(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    tokens = await register_user("+573001000001", "seller")
    headers = _auth(tokens)

    resp = await api.post(
        "/api/v1/stores", json=_store_payload("Tienda Ana", BOGOTA), headers=headers
    )
    assert resp.status_code == 201, resp.text
    store = resp.json()
    assert store["status"] == "closed"

    me = await api.get("/api/v1/me", headers=headers)
    assert me.json()["role"] == "seller"

    opened = await api.patch(
        f"/api/v1/stores/{store['id']}/status", json={"status": "open"}, headers=headers
    )
    assert opened.status_code == 200
    assert opened.json()["status"] == "open"

    found = await api.get(f"/api/v1/stores?near={BOGOTA[0]},{BOGOTA[1]}&radius=3000")
    assert found.status_code == 200
    assert store["id"] in [s["id"] for s in found.json()]


@pytest.mark.req("S-1")
async def test_list_my_stores_returns_only_owned(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    owner = _auth(await register_user("+573001000010", "seller"))
    created = await api.post(
        "/api/v1/stores", json=_store_payload("Mi Tienda", BOGOTA), headers=owner
    )
    store_id = created.json()["id"]

    mine = await api.get("/api/v1/stores/mine", headers=owner)
    assert mine.status_code == 200
    assert [s["id"] for s in mine.json()] == [store_id]

    # A different user does not see it, and non-sellers get an empty list.
    other = _auth(await register_user("+573001000011"))
    other_mine = await api.get("/api/v1/stores/mine", headers=other)
    assert other_mine.status_code == 200
    assert store_id not in [s["id"] for s in other_mine.json()]


@pytest.mark.req("S-1")
async def test_non_owner_cannot_update_store(api: AsyncClient, register_user: RegisterUser) -> None:
    owner = await register_user("+573001000002", "seller")
    resp = await api.post(
        "/api/v1/stores", json=_store_payload("Tienda Beto", BOGOTA), headers=_auth(owner)
    )
    store_id = resp.json()["id"]

    intruder = await register_user("+573001000003")
    resp = await api.patch(
        f"/api/v1/stores/{store_id}", json={"name": "Hacked"}, headers=_auth(intruder)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
