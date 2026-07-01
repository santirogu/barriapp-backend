"""Settlements I/O schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.settlements.models import Settlement, SettlementStatus


class GenerateSettlement(BaseModel):
    store_id: str
    period_start: datetime
    period_end: datetime
    due_date: datetime | None = None


class MarkPaid(BaseModel):
    payment_ref: str | None = None


class SettlementPublic(BaseModel):
    id: str
    store_id: str
    period_start: datetime
    period_end: datetime
    orders_count: int
    commission_total: int
    status: SettlementStatus
    due_date: datetime
    paid_at: datetime | None

    @classmethod
    def from_settlement(cls, s: Settlement) -> "SettlementPublic":
        return cls(
            id=str(s.id),
            store_id=str(s.store_id),
            period_start=s.period_start,
            period_end=s.period_end,
            orders_count=s.orders_count,
            commission_total=s.commission_total,
            status=s.status,
            due_date=s.due_date,
            paid_at=s.paid_at,
        )
