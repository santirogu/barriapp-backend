"""Payment and ledger models. See docs/DATA_MODEL.md §3.9-3.10 and
docs/COMMISSION_AND_SUBSCRIPTION.md."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel


class PaymentRefType(StrEnum):
    ORDER = "order"
    ERRAND = "errand"


class PaymentMethod(StrEnum):
    CASH = "cash"
    WOMPI = "wompi"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REFUNDED = "refunded"


class LedgerType(StrEnum):
    EARNING = "earning"
    COMMISSION = "commission"
    REFUND = "refund"
    PAYOUT = "payout"
    SETTLEMENT = "settlement"
    SUBSCRIPTION_FEE = "subscription_fee"


class WompiProvider(BaseModel):
    reference: str
    transaction_id: str | None = None
    wompi_status: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Payment(Document):
    ref_type: PaymentRefType
    ref_id: PydanticObjectId
    payer_id: PydanticObjectId
    amount: int  # COP
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    provider: WompiProvider | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "payments"
        indexes = [  # noqa: RUF012
            IndexModel([("ref_type", 1), ("ref_id", 1)]),
            IndexModel("provider.reference"),
            IndexModel("status"),
        ]


class LedgerEntry(Document):
    user_id: PydanticObjectId | None  # None = platform account (commission)
    type: LedgerType
    amount: int  # COP
    ref_type: PaymentRefType
    ref_id: PydanticObjectId
    store_id: PydanticObjectId | None = None  # set on order entries; enables seller settlement
    settled: bool = True  # cash commissions are unsettled until seller settlement
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "ledger_entries"
        indexes = [  # noqa: RUF012
            IndexModel([("user_id", 1), ("created_at", -1)]),
            IndexModel([("ref_type", 1), ("ref_id", 1)]),
            IndexModel([("type", 1), ("settled", 1)]),
            IndexModel([("store_id", 1), ("type", 1), ("settled", 1)]),
        ]
