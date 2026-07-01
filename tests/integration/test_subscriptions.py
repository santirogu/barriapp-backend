"""Subscription integration test: Premium reduces the store's order commission."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _order_platform_fee(
    api: AsyncClient, client_h: dict[str, str], store_id: str, product_id: str
) -> int:
    resp = await api.post(
        "/api/v1/orders",
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "qty": 1}],
            "delivery_address": {
                "label": "Casa",
                "line": "Cra 9",
                "geo": {"type": "Point", "coordinates": BOGOTA},
            },
            "payment_method": "cash",
        },
        headers=client_h,
    )
    assert resp.status_code == 201, resp.text
    return int(resp.json()["amounts"]["platform_fee"])


@pytest.mark.req("SUB-1", "SUB-2", "SUB-3")
async def test_premium_reduces_commission_and_cancel_reverts(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573110000001"))
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "Tienda",
                "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
            },
            headers=seller_h,
        )
    ).json()
    store_id = store["id"]
    await api.patch(f"/api/v1/stores/{store_id}/status", json={"status": "open"}, headers=seller_h)
    product_id = (
        await api.post(
            f"/api/v1/stores/{store_id}/products",
            json={"name": "Arroz", "price": 10000},
            headers=seller_h,
        )
    ).json()["id"]
    client_h = _auth(await register_user("+573110000002"))

    # default commission = 10%
    assert await _order_platform_fee(api, client_h, store_id, product_id) == 1000

    # subscribe to Premium → reduced 5%
    sub = await api.post(f"/api/v1/stores/{store_id}/subscription/subscribe", headers=seller_h)
    assert sub.status_code == 200, sub.text
    assert sub.json()["plan"] == "premium"
    assert sub.json()["status"] == "active"
    assert await _order_platform_fee(api, client_h, store_id, product_id) == 500

    got = await api.get(f"/api/v1/stores/{store_id}/subscription", headers=seller_h)
    assert got.json()["plan"] == "premium"

    # cancel → back to 10%
    cancelled = await api.post(f"/api/v1/stores/{store_id}/subscription/cancel", headers=seller_h)
    assert cancelled.json()["status"] == "cancelled"
    assert await _order_platform_fee(api, client_h, store_id, product_id) == 1000


@pytest.mark.req("SUB-2")
async def test_non_owner_cannot_subscribe(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h = _auth(await register_user("+573110000003"))
    store_id = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "T",
                "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
            },
            headers=seller_h,
        )
    ).json()["id"]

    intruder_h = _auth(await register_user("+573110000004"))
    resp = await api.post(f"/api/v1/stores/{store_id}/subscription/subscribe", headers=intruder_h)
    assert resp.status_code == 403
