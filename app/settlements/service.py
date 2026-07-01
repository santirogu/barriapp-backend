"""Settlements business logic: generate a seller statement, mark paid, list."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.errors import AppError
from app.payments.models import LedgerEntry, LedgerType
from app.settlements import logic
from app.settlements.models import Settlement, SettlementStatus
from app.settlements.schemas import GenerateSettlement, MarkPaid
from app.stores import repository as stores_repo
from app.users.models import User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def generate_settlement(admin: User, data: GenerateSettlement) -> Settlement:
    store_oid = PydanticObjectId(data.store_id)
    entries = await LedgerEntry.find(
        LedgerEntry.store_id == store_oid,
        LedgerEntry.type == LedgerType.COMMISSION,
        LedgerEntry.settled == False,  # noqa: E712
        LedgerEntry.created_at >= data.period_start,
        LedgerEntry.created_at <= data.period_end,
    ).to_list()

    total, orders = logic.summarize_commissions([(e.amount, str(e.ref_id)) for e in entries])
    settlement = Settlement(
        store_id=store_oid,
        period_start=data.period_start,
        period_end=data.period_end,
        orders_count=orders,
        commission_total=total,
        due_date=data.due_date or data.period_end,
    )
    await settlement.insert()

    # These commissions are now captured in a statement.
    for entry in entries:
        entry.settled = True
        await entry.save()

    await audit.record(
        module=AuditModule.PAYMENTS,
        action="settlement.created",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="settlement",
        target_id=settlement.id,
        changes={"store_id": data.store_id, "commission_total": total, "orders": orders},
    )
    return settlement


async def mark_paid(admin: User, settlement_id: PydanticObjectId, data: MarkPaid) -> Settlement:
    settlement = await Settlement.get(settlement_id)
    if settlement is None:
        raise AppError("Settlement not found", code="not_found", status_code=404)
    if settlement.status == SettlementStatus.PAID:
        return settlement
    settlement.status = SettlementStatus.PAID
    settlement.paid_at = _utcnow()
    settlement.payment_ref = data.payment_ref
    await settlement.save()
    await audit.record(
        module=AuditModule.PAYMENTS,
        action="settlement.paid",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="settlement",
        target_id=settlement.id,
    )
    return settlement


async def list_settlements(store_id: PydanticObjectId | None) -> list[Settlement]:
    criteria: dict[str, Any] = {}
    if store_id is not None:
        criteria["store_id"] = store_id
    return await Settlement.find(criteria).sort("-created_at").to_list()


async def list_for_seller(user: User) -> list[Settlement]:
    assert user.id is not None
    stores = await stores_repo.list_by_owner(user.id)
    store_ids = [s.id for s in stores]
    if not store_ids:
        return []
    return await Settlement.find({"store_id": {"$in": store_ids}}).sort("-created_at").to_list()
