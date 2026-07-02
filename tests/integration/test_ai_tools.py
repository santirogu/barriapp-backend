"""AI tool-calling integration tests: the assistant fetches live data itself (offline)."""

import pytest
from httpx import AsyncClient

from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _open_store(api: AsyncClient, seller_h: dict[str, str], name: str) -> tuple[str, str]:
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": name,
                "location": {"line": "Cra 1", "geo": {"type": "Point", "coordinates": BOGOTA}},
            },
            headers=seller_h,
        )
    ).json()
    await api.patch(
        f"/api/v1/stores/{store['id']}/status", json={"status": "open"}, headers=seller_h
    )
    product = (
        await api.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"name": "Arroz", "price": 3000},
            headers=seller_h,
        )
    ).json()
    return str(store["id"]), str(product["id"])


@pytest.mark.req("AI-3")
async def test_assistant_calls_order_tool_without_order_id(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573130000001", "seller"))
    store_id, product_id = await _open_store(api, seller_h, "Tienda")
    client_h = _auth(await register_user("+573130000002"))
    order = (
        await api.post(
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
    ).json()

    # no order_id passed — the assistant must fetch the caller's latest order itself
    chat = await api.post(
        "/api/v1/ai/chat", json={"message": "¿Dónde está mi pedido?"}, headers=client_h
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert "get_order_status" in body["tools_used"]
    assert order["code"] in body["answer"]
    assert "pending" in body["answer"]


@pytest.mark.req("AI-3")
async def test_assistant_searches_stores(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h = _auth(await register_user("+573130000003", "seller"))
    await _open_store(api, seller_h, "Tienda Ana")
    client_h = _auth(await register_user("+573130000004"))

    chat = await api.post(
        "/api/v1/ai/chat", json={"message": "¿Qué tiendas hay disponibles?"}, headers=client_h
    )
    assert chat.status_code == 200
    body = chat.json()
    assert "search_stores" in body["tools_used"]
    assert "Tienda Ana" in body["answer"]
