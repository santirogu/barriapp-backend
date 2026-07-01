"""Reviews integration tests: rate after delivery, rating recompute, dup/authz."""

import pytest
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.orders.models import Order, OrderStatus
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _store_with_product(api: AsyncClient, seller_h: dict[str, str]) -> tuple[str, str]:
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
    return str(store["id"]), str(product["id"])


async def _create_order(
    api: AsyncClient, client_h: dict[str, str], store_id: str, product_id: str
) -> str:
    order = await api.post(
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
    return str(order.json()["id"])


@pytest.mark.req("R-1", "R-2")
async def test_review_after_delivery_updates_rating(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573060000001"))
    store_id, product_id = await _store_with_product(api, seller_h)
    client_h = _auth(await register_user("+573060000002"))
    order_id = await _create_order(api, client_h, store_id, product_id)

    # a collaborator (profile exists so its rating can update)
    collab_h = _auth(await register_user("+573060000003"))
    collab_user_id = (
        await api.post(
            "/api/v1/me/become-collaborator",
            json={"vehicle_type": "bike", "id_number": "123456789"},
            headers=collab_h,
        )
    ).json()["user_id"]

    # force the order to delivered with that collaborator (bypassing the delivery flow)
    order = await Order.get(PydanticObjectId(order_id))
    assert order is not None
    order.status = OrderStatus.DELIVERED
    order.collaborator_id = PydanticObjectId(collab_user_id)
    await order.save()

    # review the store
    r = await api.post(
        "/api/v1/reviews",
        json={"order_id": order_id, "target_type": "store", "stars": 5, "comment": "Muy bien"},
        headers=client_h,
    )
    assert r.status_code == 201, r.text

    store = await api.get(f"/api/v1/stores/{store_id}")
    assert store.json()["rating"] == {"avg": 5.0, "count": 1}

    listing = await api.get(f"/api/v1/stores/{store_id}/reviews")
    assert len(listing.json()) == 1

    # duplicate store review rejected
    dup = await api.post(
        "/api/v1/reviews",
        json={"order_id": order_id, "target_type": "store", "stars": 3},
        headers=client_h,
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "already_reviewed"

    # review the collaborator → their profile rating updates
    rc = await api.post(
        "/api/v1/reviews",
        json={"order_id": order_id, "target_type": "collaborator", "stars": 4},
        headers=client_h,
    )
    assert rc.status_code == 201
    me = await api.get("/api/v1/collaborator/me", headers=collab_h)
    assert me.json()["rating"] == {"avg": 4.0, "count": 1}


@pytest.mark.req("R-1")
async def test_cannot_review_undelivered_order(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573060000004"))
    store_id, product_id = await _store_with_product(api, seller_h)
    client_h = _auth(await register_user("+573060000005"))
    order_id = await _create_order(api, client_h, store_id, product_id)  # stays pending

    resp = await api.post(
        "/api/v1/reviews",
        json={"order_id": order_id, "target_type": "store", "stars": 5},
        headers=client_h,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "not_delivered"
