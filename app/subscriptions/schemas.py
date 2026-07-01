"""Subscriptions I/O schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus


class SubscriptionPublic(BaseModel):
    store_id: str
    plan: SubscriptionPlan
    status: SubscriptionStatus
    commission_rate: float | None
    price: int
    renews_at: datetime | None

    @classmethod
    def from_subscription(cls, sub: Subscription) -> "SubscriptionPublic":
        return cls(
            store_id=str(sub.store_id),
            plan=sub.plan,
            status=sub.status,
            commission_rate=sub.commission_rate,
            price=sub.price,
            renews_at=sub.renews_at,
        )

    @classmethod
    def free(cls, store_id: str) -> "SubscriptionPublic":
        return cls(
            store_id=store_id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
            commission_rate=None,
            price=0,
            renews_at=None,
        )
