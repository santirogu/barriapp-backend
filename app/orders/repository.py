"""Data access for orders."""

from beanie import PydanticObjectId

from app.orders.models import Order


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
