"""Notifications business logic: create (in-app + push), list, mark read, tokens."""

from typing import Any

import structlog
from beanie import PydanticObjectId
from fastapi import status

from app.core.errors import AppError
from app.notifications import push
from app.notifications import repository as notif_repo
from app.notifications.models import Notification, NotificationType
from app.users import repository as users_repo
from app.users.models import User

logger = structlog.get_logger()


def with_token(tokens: list[str], token: str) -> list[str]:
    """Return the token list with ``token`` added once (pure, dedup)."""
    return tokens if token in tokens else [*tokens, token]


async def notify(
    *,
    user_id: PydanticObjectId,
    type: NotificationType,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> Notification | None:
    """Persist an in-app notification and best-effort push. Never raises."""
    payload = data or {}
    try:
        notification = Notification(
            user_id=user_id, type=type, title=title, body=body, data=payload
        )
        await notif_repo.insert(notification)
    except Exception:
        logger.exception("notification_persist_failed", user_id=str(user_id))
        return None

    try:
        user = await users_repo.get_by_id(user_id)
        if user is not None and user.device_tokens:
            await push.send_push(user.device_tokens, title, body, payload)
    except Exception:
        logger.exception("notification_push_failed", user_id=str(user_id))
    return notification


async def list_notifications(user: User, *, skip: int, limit: int) -> list[Notification]:
    assert user.id is not None
    return await notif_repo.list_by_user(user.id, skip=skip, limit=limit)


async def unread_count(user: User) -> int:
    assert user.id is not None
    return await notif_repo.count_unread(user.id)


async def mark_read(user: User, notification_id: PydanticObjectId) -> Notification:
    notification = await notif_repo.get_by_id(notification_id)
    if notification is None:
        raise AppError("Notification not found", code="not_found", status_code=404)
    if notification.user_id != user.id:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    notification.read = True
    await notification.save()
    return notification


async def register_device_token(user: User, token: str) -> None:
    user.device_tokens = with_token(user.device_tokens, token)
    await user.save()
