"""Payments integration tests: cash settlement + ledger, Wompi intent & webhook."""

import pytest
from beanie import PydanticObjectId
from httpx import AsyncClient

from app.core.config import get_settings
from app.orders.models import Order
from app.payments import service as payments_service
from app.payments.logic import wompi_signature
from app.payments.models import LedgerEntry, PaymentRefType, PaymentStatus
from tests.integration.conftest import RegisterUser

pytestmark = pytest.mark.integration

BOGOTA = [-74.081, 4.609]


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _store_with_product(api: AsyncClient, seller_h: dict[str, str]) -> str:
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
            json={"name": "Arroz", "price": 10000},
            headers=seller_h,
        )
    ).json()
    return f"{store['id']}|{product['id']}"


async def _create_order(
    api: AsyncClient, client_h: dict[str, str], store_id: str, product_id: str, method: str
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
            "payment_method": method,
        },
        headers=client_h,
    )
    assert order.status_code == 201, order.text
    return str(order.json()["id"])


@pytest.mark.req("P-1", "P-4")
async def test_cash_settlement_writes_ledger_and_is_idempotent(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573040000001", "seller"))
    store_id, product_id = (await _store_with_product(api, seller_h)).split("|")
    client_h = _auth(await register_user("+573040000002"))
    order_id = await _create_order(api, client_h, store_id, product_id, "cash")

    order = await Order.get(PydanticObjectId(order_id))
    assert order is not None
    payment = await payments_service.settle_order_payment(order)
    assert payment is not None
    assert payment.status == PaymentStatus.APPROVED
    # idempotent second call
    assert await payments_service.settle_order_payment(order) is None

    entries = await LedgerEntry.find(
        LedgerEntry.ref_type == PaymentRefType.ORDER, LedgerEntry.ref_id == order.id
    ).to_list()
    # no collaborator + zero delivery fee → commission + seller earning
    assert len(entries) == 2
    commission = next(e for e in entries if e.type.value == "commission")
    assert commission.amount == 1000  # 10% of 10000
    assert commission.settled is False  # cash → receivable from seller


@pytest.mark.req("P-2", "P-3")
async def test_wompi_intent_and_webhook_approval(
    api: AsyncClient, register_user: RegisterUser
) -> None:
    seller_h = _auth(await register_user("+573040000003", "seller"))
    store_id, product_id = (await _store_with_product(api, seller_h)).split("|")
    client_h = _auth(await register_user("+573040000004"))
    order_id = await _create_order(api, client_h, store_id, product_id, "wompi")

    intent = await api.post(
        "/api/v1/payments/intent", json={"order_id": order_id}, headers=client_h
    )
    assert intent.status_code == 200, intent.text
    body = intent.json()
    assert body["status"] == "pending"
    reference, payment_id = body["reference"], body["payment_id"]

    secret = get_settings().wompi_events_secret
    sig = wompi_signature(
        reference=reference, transaction_id="txn_1", status="APPROVED", secret=secret
    )

    # bad signature rejected
    bad = await api.post(
        "/api/v1/payments/webhook/wompi",
        json={"reference": reference, "transaction_id": "txn_1", "status": "APPROVED"},
        headers={"X-Event-Signature": "nope"},
    )
    assert bad.status_code == 401

    ok = await api.post(
        "/api/v1/payments/webhook/wompi",
        json={"reference": reference, "transaction_id": "txn_1", "status": "APPROVED"},
        headers={"X-Event-Signature": sig},
    )
    assert ok.status_code == 200

    got = await api.get(f"/api/v1/payments/{payment_id}", headers=client_h)
    assert got.json()["status"] == "approved"

    entries = await LedgerEntry.find(
        LedgerEntry.ref_type == PaymentRefType.ORDER,
        LedgerEntry.ref_id == PydanticObjectId(order_id),
    ).to_list()
    commission = next(e for e in entries if e.type.value == "commission")
    assert commission.settled is True  # wompi → platform holds funds
