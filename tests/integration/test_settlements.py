"""Settlement integration tests: generate from cash commissions, pay, seller view."""

from datetime import UTC, datetime, timedelta

import pytest
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.orders.models import Order
from app.payments import service as payments_service
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


@pytest.mark.req("P-7")
async def test_generate_pay_and_seller_view(api: AsyncClient, register_user: RegisterUser) -> None:
    seller_h = _auth(await register_user("+573100000001"))
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
    product = (
        await api.post(
            f"/api/v1/stores/{store_id}/products",
            json={"name": "Arroz", "price": 10000},
            headers=seller_h,
        )
    ).json()
    client_h = _auth(await register_user("+573100000002"))
    order_id = (
        await api.post(
            "/api/v1/orders",
            json={
                "store_id": store_id,
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

    # settle the cash order → writes an unsettled commission ledger entry (store-tagged)
    order = await Order.get(PydanticObjectId(order_id))
    assert order is not None
    await payments_service.settle_order_payment(order)

    admin_h = _auth(await register_user("+573100000003"))
    await _promote_to_admin("+573100000003")

    now = datetime.now(UTC)
    gen = await api.post(
        "/api/v1/admin/settlements",
        json={
            "store_id": store_id,
            "period_start": (now - timedelta(days=1)).isoformat(),
            "period_end": (now + timedelta(days=1)).isoformat(),
        },
        headers=admin_h,
    )
    assert gen.status_code == 201, gen.text
    settlement = gen.json()
    assert settlement["commission_total"] == 1000  # 10% of 10000
    assert settlement["orders_count"] == 1
    assert settlement["status"] == "pending"

    paid = await api.post(
        f"/api/v1/admin/settlements/{settlement['id']}/pay",
        json={"payment_ref": "nequi-123"},
        headers=admin_h,
    )
    assert paid.json()["status"] == "paid"

    # seller sees their settlement
    mine = await api.get("/api/v1/settlements", headers=seller_h)
    assert settlement["id"] in [s["id"] for s in mine.json()]


@pytest.mark.req("P-7")
async def test_generate_requires_admin(api: AsyncClient, register_user: RegisterUser) -> None:
    client_h = _auth(await register_user("+573100000004"))
    now = datetime.now(UTC)
    resp = await api.post(
        "/api/v1/admin/settlements",
        json={
            "store_id": str(PydanticObjectId()),
            "period_start": (now - timedelta(days=1)).isoformat(),
            "period_end": now.isoformat(),
        },
        headers=client_h,
    )
    assert resp.status_code == 403
