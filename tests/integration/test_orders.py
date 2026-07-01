"""Orders integration tests: lifecycle, totals, stock, ownership (O-1..O-5)."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _seller_with_product(
    api: AsyncClient, register_user: RegisterUser, phone: str, *, price: int, stock: int
) -> tuple[dict[str, str], str, str]:
    headers = _auth(await register_user(phone))
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "Tienda Ana",
                "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
            },
            headers=headers,
        )
    ).json()
    await api.patch(
        f"/api/v1/stores/{store['id']}/status", json={"status": "open"}, headers=headers
    )
    product = (
        await api.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"name": "Arroz 500g", "price": price, "stock": stock},
            headers=headers,
        )
    ).json()
    return headers, str(store["id"]), str(product["id"])


def _order_payload(store_id: str, product_id: str, qty: int) -> dict[str, object]:
    return {
        "store_id": store_id,
        "items": [{"product_id": product_id, "qty": qty}],
        "delivery_address": {
            "label": "Casa",
            "line": "Cra 9 #1-1",
            "geo": {"type": "Point", "coordinates": BOGOTA},
        },
        "payment_method": "cash",
    }


@pytest.mark.req("O-1", "O-2", "O-3", "O-5")
async def test_order_lifecycle_and_totals(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h, store_id, product_id = await _seller_with_product(
        api, register_user, "+573010000001", price=3500, stock=10
    )
    client_h = _auth(await register_user("+573010000002"))

    created = await api.post(
        "/api/v1/orders", json=_order_payload(store_id, product_id, 2), headers=client_h
    )
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["status"] == "pending"
    assert order["amounts"]["items_total"] == 7000
    assert order["amounts"]["platform_fee"] == 700  # 10% default commission
    assert order["amounts"]["total"] == 7000  # default base_fee 0
    order_id = order["id"]

    # seller drives the status forward
    assert (await api.post(f"/api/v1/orders/{order_id}/accept", headers=seller_h)).json()[
        "status"
    ] == "accepted"
    assert (
        await api.post(
            f"/api/v1/orders/{order_id}/status", json={"status": "preparing"}, headers=seller_h
        )
    ).json()["status"] == "preparing"
    ready = await api.post(
        f"/api/v1/orders/{order_id}/status", json={"status": "ready"}, headers=seller_h
    )
    assert ready.json()["status"] == "ready"

    # client sees it in their history
    mine = await api.get("/api/v1/orders", headers=client_h)
    assert order_id in [o["id"] for o in mine.json()]


@pytest.mark.req("O-4", "O-6")
async def test_cancel_restores_stock(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h, store_id, product_id = await _seller_with_product(
        api, register_user, "+573010000003", price=1000, stock=5
    )
    client_h = _auth(await register_user("+573010000004"))

    created = await api.post(
        "/api/v1/orders", json=_order_payload(store_id, product_id, 3), headers=client_h
    )
    order_id = created.json()["id"]

    after_order = (await api.get(f"/api/v1/products/{product_id}")).json()
    assert after_order["stock"] == 2  # 5 - 3

    cancelled = await api.post(
        f"/api/v1/orders/{order_id}/cancel", json={"reason": "changed mind"}, headers=client_h
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    restored = (await api.get(f"/api/v1/products/{product_id}")).json()
    assert restored["stock"] == 5


@pytest.mark.req("O-5")
async def test_stranger_cannot_read_order(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h, store_id, product_id = await _seller_with_product(
        api, register_user, "+573010000005", price=1000, stock=5
    )
    client_h = _auth(await register_user("+573010000006"))
    order_id = (
        await api.post(
            "/api/v1/orders", json=_order_payload(store_id, product_id, 1), headers=client_h
        )
    ).json()["id"]

    stranger_h = _auth(await register_user("+573010000007"))
    resp = await api.get(f"/api/v1/orders/{order_id}", headers=stranger_h)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


@pytest.mark.req("O-2")
async def test_seller_lists_store_orders(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h, store_id, product_id = await _seller_with_product(
        api, register_user, "+573010000008", price=1000, stock=5
    )
    client_h = _auth(await register_user("+573010000009"))
    order_id = (
        await api.post(
            "/api/v1/orders", json=_order_payload(store_id, product_id, 1), headers=client_h
        )
    ).json()["id"]

    # owner sees the order in the store queue
    queue = await api.get(f"/api/v1/stores/{store_id}/orders", headers=seller_h)
    assert queue.status_code == 200
    assert order_id in [o["id"] for o in queue.json()]

    # status filter works
    pending = await api.get(f"/api/v1/stores/{store_id}/orders?status=pending", headers=seller_h)
    assert order_id in [o["id"] for o in pending.json()]
    delivered = await api.get(
        f"/api/v1/stores/{store_id}/orders?status=delivered", headers=seller_h
    )
    assert order_id not in [o["id"] for o in delivered.json()]

    # a non-owner cannot read the store's orders
    stranger_h = _auth(await register_user("+573010000012"))
    forbidden = await api.get(f"/api/v1/stores/{store_id}/orders", headers=stranger_h)
    assert forbidden.status_code == 403
