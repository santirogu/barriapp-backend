"""AI assistant integration tests: ingest knowledge, grounded RAG chat (offline)."""

import pytest
from httpx import AsyncClient

from app.users.models import Role, User
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _promote_to_admin(phone: str) -> None:
    user = await User.find_one(User.phone == phone)
    assert user is not None
    user.role = Role.SUPER_ADMIN
    await user.save()


@pytest.mark.req("AI-1", "AI-2", "AI-4")
async def test_ingest_and_chat_uses_knowledge(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    admin_h = _auth(await register_user("+573120000001"))
    await _promote_to_admin("+573120000001")

    ing = await api.post(
        "/api/v1/ai/knowledge",
        json={
            "content": "Puedes pagar en efectivo o con Wompi al recibir tu pedido.",
            "source_type": "faq",
        },
        headers=admin_h,
    )
    assert ing.status_code == 201, ing.text

    client_h = _auth(await register_user("+573120000002"))
    chat = await api.post(
        "/api/v1/ai/chat",
        json={"message": "¿Cómo puedo pagar mi pedido?"},
        headers=client_h,
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert "Wompi" in body["answer"]  # grounded in the ingested knowledge
    assert len(body["sources"]) >= 1
    conversation_id = body["conversation_id"]

    # conversation persisted with the exchange
    conv = await api.get(f"/api/v1/ai/conversations/{conversation_id}", headers=client_h)
    assert conv.status_code == 200
    roles = [m["role"] for m in conv.json()["messages"]]
    assert roles == ["user", "assistant"]


@pytest.mark.req("AI-3")
async def test_chat_grounds_on_order_status(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h = _auth(await register_user("+573120000003", "seller"))
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
    await api.patch(
        f"/api/v1/stores/{store['id']}/status", json={"status": "open"}, headers=seller_h
    )
    product_id = (
        await api.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"name": "Arroz", "price": 3000},
            headers=seller_h,
        )
    ).json()["id"]

    client_h = _auth(await register_user("+573120000004"))
    order = await api.post(
        "/api/v1/orders",
        json={
            "store_id": store["id"],
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
    order_body = order.json()

    chat = await api.post(
        "/api/v1/ai/chat",
        json={"message": "¿Dónde está mi pedido?", "order_id": order_body["id"]},
        headers=client_h,
    )
    assert chat.status_code == 200
    answer = chat.json()["answer"]
    assert order_body["code"] in answer
    assert "pending" in answer


@pytest.mark.req("AI-1")
async def test_knowledge_ingest_requires_admin(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    client_h = _auth(await register_user("+573120000005"))
    resp = await api.post(
        "/api/v1/ai/knowledge", json={"content": "x", "source_type": "faq"}, headers=client_h
    )
    assert resp.status_code == 403
