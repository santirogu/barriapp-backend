"""Data access for notifications."""

from beanie import PydanticObjectId

from app.notifications.models import Notification


async def insert(notification: Notification) -> Notification:
    return await notification.insert()


async def get_by_id(notification_id: PydanticObjectId) -> Notification | None:
    return await Notification.get(notification_id)


async def list_by_user(
    user_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Notification]:
    return (
        await Notification.find(Notification.user_id == user_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_unread(user_id: PydanticObjectId) -> int:
    return await Notification.find(
        Notification.user_id == user_id,
        Notification.read == False,  # noqa: E712
    ).count()
