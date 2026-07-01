"""Seller settlement statement model. See docs/COMMISSION_AND_SUBSCRIPTION.md §5."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class SettlementStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Settlement(Document):
    store_id: PydanticObjectId
    period_start: datetime
    period_end: datetime
    orders_count: int
    commission_total: int  # COP owed by the seller to the platform
    status: SettlementStatus = SettlementStatus.PENDING
    due_date: datetime
    paid_at: datetime | None = None
    payment_ref: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "settlements"
        indexes = [  # noqa: RUF012
            IndexModel([("store_id", 1), ("created_at", -1)]),
            IndexModel("status"),
        ]
