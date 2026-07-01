"""Notifications endpoints. See docs/API_CONTRACT.md §12."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.notifications import service
from app.notifications.schemas import (
    DeviceTokenIn,
    NotificationPublic,
    UnreadCount,
)

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationPublic])
async def list_notifications(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[NotificationPublic]:
    items = await service.list_notifications(user, skip=(page - 1) * limit, limit=limit)
    return [NotificationPublic.from_notification(n) for n in items]


@router.get("/notifications/unread-count", response_model=UnreadCount)
async def unread_count(user: CurrentUser) -> UnreadCount:
    return UnreadCount(unread=await service.unread_count(user))


@router.post("/notifications/{notification_id}/read", response_model=NotificationPublic)
async def mark_read(notification_id: PydanticObjectId, user: CurrentUser) -> NotificationPublic:
    return NotificationPublic.from_notification(await service.mark_read(user, notification_id))


@router.post("/me/device-tokens", status_code=status.HTTP_204_NO_CONTENT)
async def register_device_token(data: DeviceTokenIn, user: CurrentUser) -> None:
    await service.register_device_token(user, data.token)
