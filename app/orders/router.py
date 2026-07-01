"""Orders endpoints. See docs/API_CONTRACT.md §6 and docs/ORDER_FLOW.md."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.orders import service
from app.orders.schemas import (
    OrderCancel,
    OrderCreate,
    OrderPublic,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, user: CurrentUser) -> OrderPublic:
    return OrderPublic.from_order(await service.create_order(user, data))


@router.get("", response_model=list[OrderPublic])
async def list_my_orders(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[OrderPublic]:
    orders = await service.list_my_orders(user, skip=(page - 1) * limit, limit=limit)
    return [OrderPublic.from_order(o) for o in orders]


@router.get("/{order_id}", response_model=OrderPublic)
async def get_order(order_id: PydanticObjectId, user: CurrentUser) -> OrderPublic:
    return OrderPublic.from_order(await service.get_order(user, order_id))


@router.post("/{order_id}/accept", response_model=OrderPublic)
async def accept_order(order_id: PydanticObjectId, user: CurrentUser) -> OrderPublic:
    return OrderPublic.from_order(await service.accept_order(user, order_id))


@router.post("/{order_id}/status", response_model=OrderPublic)
async def advance_status(
    order_id: PydanticObjectId, data: OrderStatusUpdate, user: CurrentUser
) -> OrderPublic:
    return OrderPublic.from_order(await service.advance_status(user, order_id, data))


@router.post("/{order_id}/cancel", response_model=OrderPublic)
async def cancel_order(
    order_id: PydanticObjectId, data: OrderCancel, user: CurrentUser
) -> OrderPublic:
    return OrderPublic.from_order(await service.cancel_order(user, order_id, data))
