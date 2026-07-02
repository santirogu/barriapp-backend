"""Payments business logic: cash settlement on delivery, Wompi intent & webhook."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.config import get_settings
from app.core.errors import AppError
from app.orders import repository as orders_repo
from app.orders.models import Order
from app.orders.models import PaymentMethod as OrderPaymentMethod
from app.payments import logic
from app.payments import repository as payments_repo
from app.payments.logic import LedgerLine
from app.payments.models import (
    LedgerEntry,
    Payment,
    PaymentMethod,
    PaymentRefType,
    PaymentStatus,
    WompiProvider,
)
from app.payments.schemas import IntentResponse, WompiWebhookIn
from app.stores import repository as stores_repo
from app.users.models import Role, User


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _write_ledger(
    lines: list[LedgerLine],
    ref_type: PaymentRefType,
    ref_id: PydanticObjectId,
    store_id: PydanticObjectId | None = None,
) -> None:
    for line in lines:
        entry = LedgerEntry(
            user_id=PydanticObjectId(line.user_id) if line.user_id else None,
            type=line.type,
            amount=line.amount,
            ref_type=ref_type,
            ref_id=ref_id,
            store_id=store_id,
            settled=line.settled,
        )
        await payments_repo.insert_ledger(entry)
    await audit.record(
        module=AuditModule.PAYMENTS,
        action="ledger.entry.created",
        target_type=ref_type.value,
        target_id=ref_id,
        changes={"lines": len(lines)},
    )


async def _ledger_for_order(order: Order, *, settled: bool) -> None:
    store = await stores_repo.get_by_id(order.store_id)
    if store is None:
        return
    lines = logic.compute_ledger_lines(
        items_total=order.amounts.items_total,
        delivery_fee=order.amounts.delivery_fee,
        platform_fee=order.amounts.platform_fee,
        collaborator_id=str(order.collaborator_id) if order.collaborator_id else None,
        seller_id=str(store.owner_id),
        settled=settled,
    )
    assert order.id is not None
    await _write_ledger(lines, PaymentRefType.ORDER, order.id, store_id=store.id)


async def settle_order_payment(order: Order) -> Payment | None:
    """Record a cash payment as approved and write the ledger, once, on delivery."""
    assert order.id is not None
    if await payments_repo.get_payment_by_ref(PaymentRefType.ORDER, order.id) is not None:
        return None  # idempotent — already settled/intented

    payment = Payment(
        ref_type=PaymentRefType.ORDER,
        ref_id=order.id,
        payer_id=order.client_id,
        amount=order.amounts.total,
        method=PaymentMethod(str(order.payment_method)),
        status=PaymentStatus.APPROVED,
    )
    await payments_repo.insert_payment(payment)
    order.payment_id = payment.id
    await order.save()

    # Cash: platform commission is a receivable from the seller (unsettled).
    await _ledger_for_order(order, settled=False)
    await audit.record(
        module=AuditModule.PAYMENTS,
        action="payment.approved",
        actor_id=order.client_id,
        target_type="order",
        target_id=order.id,
        changes={"method": "cash", "amount": order.amounts.total},
    )
    return payment


async def settle_errand_payment(
    *,
    errand_id: PydanticObjectId,
    client_id: PydanticObjectId,
    collaborator_id: PydanticObjectId | None,
    offered_fee: int,
) -> Payment | None:
    """Record a cash errand payment (approved) and credit the collaborator's fee.

    Errands take no platform commission at launch. Idempotent per errand.
    """
    if await payments_repo.get_payment_by_ref(PaymentRefType.ERRAND, errand_id) is not None:
        return None

    payment = Payment(
        ref_type=PaymentRefType.ERRAND,
        ref_id=errand_id,
        payer_id=client_id,
        amount=offered_fee,
        method=PaymentMethod.CASH,
        status=PaymentStatus.APPROVED,
    )
    await payments_repo.insert_payment(payment)

    lines: list[LedgerLine] = []
    if collaborator_id is not None and offered_fee > 0:
        from app.payments.models import LedgerType

        lines.append(
            LedgerLine(
                type=LedgerType.EARNING,
                user_id=str(collaborator_id),
                amount=offered_fee,
                settled=True,
            )
        )
    if lines:
        await _write_ledger(lines, PaymentRefType.ERRAND, errand_id)

    await audit.record(
        module=AuditModule.PAYMENTS,
        action="payment.approved",
        actor_id=client_id,
        target_type="errand",
        target_id=errand_id,
        changes={"method": "cash", "amount": offered_fee},
    )
    return payment


async def create_intent(user: User, order_id: PydanticObjectId) -> IntentResponse:
    order = await orders_repo.get_by_id(order_id)
    if order is None:
        raise AppError("Order not found", code="not_found", status_code=404)
    if order.client_id != user.id:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if order.payment_method != OrderPaymentMethod.WOMPI:
        raise AppError("Order is not a Wompi payment", code="not_wompi", status_code=409)

    settings = get_settings()
    assert order.id is not None
    existing = await payments_repo.get_payment_by_ref(PaymentRefType.ORDER, order.id)
    payment = existing
    if payment is None:
        payment = Payment(
            ref_type=PaymentRefType.ORDER,
            ref_id=order.id,
            payer_id=user.id,
            amount=order.amounts.total,
            method=PaymentMethod.WOMPI,
            status=PaymentStatus.PENDING,
            provider=WompiProvider(reference=f"BA-{order.code}", wompi_status="PENDING"),
        )
        await payments_repo.insert_payment(payment)
        await audit.record(
            module=AuditModule.PAYMENTS,
            action="payment.intent.created",
            actor_id=user.id,
            target_type="order",
            target_id=order.id,
        )

    assert payment.provider is not None
    return IntentResponse(
        payment_id=str(payment.id),
        reference=payment.provider.reference,
        amount=payment.amount,
        currency=settings.payment_currency,
        public_key=settings.wompi_public_key,
        status=payment.status,
    )


async def handle_wompi_webhook(payload: WompiWebhookIn, signature: str | None) -> Payment:
    settings = get_settings()
    if signature is None or not logic.verify_wompi_signature(
        reference=payload.reference,
        transaction_id=payload.transaction_id,
        status=payload.status,
        secret=settings.wompi_events_secret,
        provided=signature,
    ):
        raise AppError(
            "Invalid signature", code="invalid_signature", status_code=status.HTTP_401_UNAUTHORIZED
        )

    payment = await payments_repo.get_payment_by_reference(payload.reference)
    if payment is None:
        raise AppError("Payment not found", code="not_found", status_code=404)
    if payment.status == PaymentStatus.APPROVED:
        return payment  # idempotent

    assert payment.provider is not None
    payment.provider.transaction_id = payload.transaction_id
    payment.provider.wompi_status = payload.status
    payment.updated_at = _utcnow()

    if payload.status == "APPROVED":
        payment.status = PaymentStatus.APPROVED
        await payment.save()
        order = await orders_repo.get_by_id(payment.ref_id)
        if order is not None:
            order.payment_id = payment.id
            await order.save()
            # Wompi (prepaid): the platform holds funds, so commission is settled.
            await _ledger_for_order(order, settled=True)
        await audit.record(
            module=AuditModule.PAYMENTS,
            action="payment.approved",
            target_type="payment",
            target_id=payment.id,
            changes={"method": "wompi"},
        )
    else:
        payment.status = PaymentStatus.DECLINED
        await payment.save()
        await audit.record(
            module=AuditModule.PAYMENTS,
            action="payment.declined",
            target_type="payment",
            target_id=payment.id,
        )
    return payment


async def get_payment(user: User, payment_id: PydanticObjectId) -> Payment:
    payment = await payments_repo.get_payment(payment_id)
    if payment is None:
        raise AppError("Payment not found", code="not_found", status_code=404)
    if payment.payer_id != user.id and user.role != Role.SUPER_ADMIN:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    return payment
