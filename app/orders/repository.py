"""Data access for orders."""

from beanie import PydanticObjectId

from app.orders.models import Order, OrderStatus


async def get_by_id(order_id: PydanticObjectId) -> Order | None:
    return await Order.get(order_id)


async def insert(order: Order) -> Order:
    return await order.insert()


async def list_by_client(
    client_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Order]:
    return (
        await Order.find(Order.client_id == client_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def list_by_store(
    store_id: PydanticObjectId,
    *,
    order_status: OrderStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Order]:
    query = Order.find(Order.store_id == store_id)
    if order_status is not None:
        query = query.find(Order.status == order_status)
    return await query.sort("-created_at").skip(skip).limit(limit).to_list()
