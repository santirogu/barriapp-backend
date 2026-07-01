"""Seller subscription model. See docs/COMMISSION_AND_SUBSCRIPTION.md §6."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class SubscriptionPlan(StrEnum):
    FREE = "free"
    PREMIUM = "premium"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Subscription(Document):
    store_id: PydanticObjectId
    plan: SubscriptionPlan = SubscriptionPlan.PREMIUM
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    commission_rate: float | None = None  # reduced rate applied while active
    price: int = 0  # COP / month
    started_at: datetime = Field(default_factory=_utcnow)
    renews_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "subscriptions"
        indexes = [  # noqa: RUF012
            IndexModel("store_id", unique=True),
            IndexModel("status"),
        ]
