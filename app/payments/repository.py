"""Data access for payments and ledger entries."""

from beanie import PydanticObjectId

from app.payments.models import LedgerEntry, Payment, PaymentRefType


async def get_payment(payment_id: PydanticObjectId) -> Payment | None:
    return await Payment.get(payment_id)


async def insert_payment(payment: Payment) -> Payment:
    return await payment.insert()


async def get_payment_by_ref(ref_type: PaymentRefType, ref_id: PydanticObjectId) -> Payment | None:
    return await Payment.find_one(Payment.ref_type == ref_type, Payment.ref_id == ref_id)


async def get_payment_by_reference(reference: str) -> Payment | None:
    return await Payment.find_one({"provider.reference": reference})


async def insert_ledger(entry: LedgerEntry) -> LedgerEntry:
    return await entry.insert()


async def list_ledger_by_ref(
    ref_type: PaymentRefType, ref_id: PydanticObjectId
) -> list[LedgerEntry]:
    return await LedgerEntry.find(
        LedgerEntry.ref_type == ref_type, LedgerEntry.ref_id == ref_id
    ).to_list()
