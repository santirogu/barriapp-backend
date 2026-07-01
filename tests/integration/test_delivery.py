"""Delivery integration tests: assign nearest collaborator, lifecycle, order sync."""

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
    user.roles.append(Role.SUPER_ADMIN)
    await user.save()


async def _ready_order(
    api: AsyncClient, register_user: RegisterUser, seller_phone: str, client_phone: str
) -> tuple[dict[str, str], str]:
    seller_h = _auth(await register_user(seller_phone))
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "Tienda Ana",
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
    order = (
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
    ).json()
    order_id = order["id"]
    await api.post(f"/api/v1/orders/{order_id}/accept", headers=seller_h)
    await api.post(
        f"/api/v1/orders/{order_id}/status", json={"status": "preparing"}, headers=seller_h
    )
    await api.post(f"/api/v1/orders/{order_id}/status", json={"status": "ready"}, headers=seller_h)
    return seller_h, order_id


async def _online_collaborator(
    api: AsyncClient, register_user: RegisterUser, phone: str, admin_h: dict[str, str]
) -> dict[str, str]:
    collab_h = _auth(await register_user(phone))
    profile = (
        await api.post(
            "/api/v1/me/become-collaborator",
            json={"vehicle_type": "bike", "id_number": "123456789"},
            headers=collab_h,
        )
    ).json()
    await api.patch(
        f"/api/v1/collaborator/{profile['user_id']}/verification",
        json={"status": "approved"},
        headers=admin_h,
    )
    await api.post(
        "/api/v1/collaborator/availability",
        json={"status": "online", "lng": BOGOTA[0], "lat": BOGOTA[1]},
        headers=collab_h,
    )
    return collab_h


@pytest.mark.req("D-1", "D-3", "D-4", "D-5")
async def test_assign_and_full_delivery_flow(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h, order_id = await _ready_order(api, register_user, "+573030000001", "+573030000002")
    admin_h = _auth(await register_user("+573030000009"))
    await _promote_to_admin("+573030000009")
    collab_h = await _online_collaborator(api, register_user, "+573030000003", admin_h)

    # seller assigns → nearest online collaborator
    assigned = await api.post(f"/api/v1/orders/{order_id}/assign", headers=seller_h)
    assert assigned.status_code == 201, assigned.text
    delivery = assigned.json()
    assert delivery["status"] == "assigned"
    delivery_id = delivery["id"]

    # collaborator drives the delivery; order status syncs
    for target in ("en_route_pickup", "picked_up", "en_route_dropoff", "delivered"):
        resp = await api.post(
            f"/api/v1/deliveries/{delivery_id}/status", json={"status": target}, headers=collab_h
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == target
        if target == "picked_up":
            await api.post(
                f"/api/v1/deliveries/{delivery_id}/location",
                json={"lng": -74.080, "lat": 4.610},
                headers=collab_h,
            )
        if target == "en_route_dropoff":
            proof = await api.post(
                f"/api/v1/deliveries/{delivery_id}/proof",
                json={"photo_url": "https://img/proof.jpg", "received_by": "Ana"},
                headers=collab_h,
            )
            assert proof.status_code == 200

    # order reflects delivered and exposes the delivery id (for client tracking)
    order = await api.get(f"/api/v1/orders/{order_id}", headers=seller_h)
    assert order.json()["status"] == "delivered"
    assert order.json()["delivery_id"] == delivery_id

    # collaborator sees the job
    jobs = await api.get("/api/v1/collaborator/jobs", headers=collab_h)
    assert delivery_id in [d["id"] for d in jobs.json()]


@pytest.mark.req("D-1")
async def test_assign_requires_ready_order(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h = _auth(await register_user("+573030000004"))
    store = (
        await api.post(
            "/api/v1/stores",
            json={
                "name": "T",
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
            json={"name": "X", "price": 1000},
            headers=seller_h,
        )
    ).json()
    client_h = _auth(await register_user("+573030000005"))
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

    # order is still pending → cannot assign
    resp = await api.post(f"/api/v1/orders/{order_id}/assign", headers=seller_h)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "order_not_ready"
