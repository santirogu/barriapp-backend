"""Catalog integration tests: product management & ownership (S-3, S-5)."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_store(api: AsyncClient, tokens: dict[str, str], name: str) -> str:
    resp = await api.post(
        "/api/v1/stores",
        json={
            "name": name,
            "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
        },
        headers=_auth(tokens),
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


@pytest.mark.req("S-3", "S-5")
async def test_add_list_and_toggle_product(api: AsyncClient, register_user: RegisterUser) -> None:
    tokens = await register_user("+573002000001")
    headers = _auth(tokens)
    store_id = await _create_store(api, tokens, "Tienda Ana")

    resp = await api.post(
        f"/api/v1/stores/{store_id}/products",
        json={"name": "Arroz 500g", "price": 3500, "unit": "und"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    product = resp.json()
    assert product["price"] == 3500
    assert product["is_available"] is True

    listing = await api.get(f"/api/v1/stores/{store_id}/products")
    assert listing.status_code == 200
    assert product["id"] in [p["id"] for p in listing.json()]

    toggled = await api.patch(
        f"/api/v1/products/{product['id']}", json={"is_available": False}, headers=headers
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_available"] is False


@pytest.mark.req("S-3")
async def test_non_owner_cannot_add_product(api: AsyncClient, register_user: RegisterUser) -> None:
    owner = await register_user("+573002000002")
    store_id = await _create_store(api, owner, "Tienda Beto")

    intruder = await register_user("+573002000003")
    resp = await api.post(
        f"/api/v1/stores/{store_id}/products",
        json={"name": "X", "price": 100},
        headers=_auth(intruder),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
