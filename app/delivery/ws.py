"""Live delivery tracking over WebSocket.

Clients connect to ``/ws/deliveries/{id}?token=<accessToken>`` and receive an
initial snapshot followed by live status/location updates that the delivery
service publishes to Redis (`delivery:{id}`). See docs/ORDER_FLOW.md §5.
"""

import structlog
from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jwt import PyJWTError

from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.delivery import service as delivery_service
from app.delivery.models import Delivery
from app.users import repository as users_repo
from app.users.models import User, UserStatus

logger = structlog.get_logger()

router = APIRouter()

# Custom WS close codes.
_WS_UNAUTHENTICATED = 4401
_WS_FORBIDDEN = 4403
_WS_BAD_REQUEST = 4400


async def resolve_ws_user(token: str | None) -> User | None:
    """Resolve an access token (from the WS query string) to an active user."""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except PyJWTError:
        return None
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        return None
    subject = payload.get("sub")
    if not subject:
        return None
    user = await users_repo.get_by_id(PydanticObjectId(subject))
    if user is None or user.status == UserStatus.SUSPENDED:
        return None
    return user


def _snapshot(delivery: Delivery) -> dict[str, object]:
    return {
        "delivery_id": str(delivery.id),
        "status": str(delivery.status),
        "route": [p.coordinates for p in delivery.route[-1:]],
    }


@router.websocket("/ws/deliveries/{delivery_id}")
async def track_delivery(websocket: WebSocket, delivery_id: str) -> None:
    user = await resolve_ws_user(websocket.query_params.get("token"))
    if user is None:
        await websocket.close(code=_WS_UNAUTHENTICATED)
        return
    try:
        oid = PydanticObjectId(delivery_id)
    except (InvalidId, ValueError):
        await websocket.close(code=_WS_BAD_REQUEST)
        return
    try:
        delivery = await delivery_service.get_delivery(user, oid)
    except AppError:
        await websocket.close(code=_WS_FORBIDDEN)
        return

    await websocket.accept()

    # Subscribe BEFORE sending the snapshot so no update published between the
    # snapshot and the subscription is missed.
    channel = f"delivery:{oid}"
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel)
    await websocket.send_json(_snapshot(delivery))
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        logger.debug("ws_delivery_client_disconnected", delivery_id=delivery_id)
    except Exception:
        logger.exception("ws_delivery_stream_failed", delivery_id=delivery_id)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()  # type: ignore[no-untyped-call]
