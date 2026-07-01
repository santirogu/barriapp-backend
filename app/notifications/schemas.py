"""Notifications I/O schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.notifications.models import Notification, NotificationType


class NotificationPublic(BaseModel):
    id: str
    type: NotificationType
    title: str
    body: str
    data: dict[str, Any]
    read: bool
    created_at: datetime

    @classmethod
    def from_notification(cls, n: Notification) -> "NotificationPublic":
        return cls(
            id=str(n.id),
            type=n.type,
            title=n.title,
            body=n.body,
            data=n.data,
            read=n.read,
            created_at=n.created_at,
        )


class UnreadCount(BaseModel):
    unread: int


class DeviceTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
