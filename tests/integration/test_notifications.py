"""Notifications integration tests: order events notify, read, device tokens."""

import pytest
from httpx import AsyncClient

from app.users.models import User
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _accepted_order(
    api: AsyncClient, register_user: RegisterUser, seller_phone: str, client_phone: str
) -> dict[str, str]:
    seller_h = _auth(await register_user(seller_phone, "seller"))
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
    product = (
        await api.post(
            f"/api/v1/stores/{store['id']}/products",
            json={"name": "Arroz", "price": 3000},
            headers=seller_h,
        )
    ).json()
    client_h = _auth(await register_user(client_phone))
    order_id = (
        await api.post(
            "/api/v1/orders",
            json={
                "store_id": store["id"],
                "items": [{"product_id": product["id"], "qty": 1}],
                "delivery_address": {
                    "label": "Casa",
                    "line": "Cra 9",
                    "geo": {"type": "Point", "coordinates": BOGOTA},
                },
                "payment_method": "cash",
            },
            headers=client_h,
        )
    ).json()["id"]
    await api.post(f"/api/v1/orders/{order_id}/accept", headers=seller_h)
    return client_h


@pytest.mark.req("N-1", "N-2")
async def test_order_event_creates_notification_and_mark_read(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    client_h = await _accepted_order(api, register_user, "+573070000001", "+573070000002")

    listing = await api.get("/api/v1/notifications", headers=client_h)
    assert listing.status_code == 200
    items = listing.json()
    assert any(n["type"] == "order_update" for n in items)

    assert (await api.get("/api/v1/notifications/unread-count", headers=client_h)).json()[
        "unread"
    ] >= 1

    notif_id = items[0]["id"]
    read = await api.post(f"/api/v1/notifications/{notif_id}/read", headers=client_h)
    assert read.status_code == 200
    assert read.json()["read"] is True


@pytest.mark.req("U-3")
async def test_register_device_token_is_idempotent(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    phone = "+573070000003"
    client_h = _auth(await register_user(phone))

    for _ in range(2):
        resp = await api.post(
            "/api/v1/me/device-tokens", json={"token": "fcm-token-abc"}, headers=client_h
        )
        assert resp.status_code == 204

    user = await User.find_one(User.phone == phone)
    assert user is not None
    assert user.device_tokens == ["fcm-token-abc"]  # no duplicate


@pytest.mark.req("N-2")
async def test_cannot_mark_other_users_notification(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    client_h = await _accepted_order(api, register_user, "+573070000004", "+573070000005")
    notif_id = (await api.get("/api/v1/notifications", headers=client_h)).json()[0]["id"]

    stranger_h = _auth(await register_user("+573070000006"))
    resp = await api.post(f"/api/v1/notifications/{notif_id}/read", headers=stranger_h)
    assert resp.status_code == 403
