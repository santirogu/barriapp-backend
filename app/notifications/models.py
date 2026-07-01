"""Notification model. See docs/DATA_MODEL.md §3.12."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class NotificationType(StrEnum):
    ORDER_UPDATE = "order_update"
    ERRAND_UPDATE = "errand_update"
    DELIVERY_UPDATE = "delivery_update"
    SYSTEM = "system"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Notification(Document):
    user_id: PydanticObjectId
    type: NotificationType
    title: str
    body: str
    data: dict[str, Any] = Field(default_factory=dict)
    read: bool = False
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "notifications"
        indexes = [  # noqa: RUF012
            IndexModel([("user_id", 1), ("read", 1), ("created_at", -1)]),
        ]
