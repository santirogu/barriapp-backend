"""Orders I/O schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.orders.models import (
    Order,
    OrderAmounts,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    StatusEvent,
)
from app.users.models import Address


class OrderItemInput(BaseModel):
    product_id: str
    qty: int = Field(ge=1)


class OrderCreate(BaseModel):
    store_id: str
    items: list[OrderItemInput] = Field(min_length=1)
    delivery_address: Address
    payment_method: PaymentMethod
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderCancel(BaseModel):
    reason: str | None = None


class OrderPublic(BaseModel):
    id: str
    code: str
    client_id: str
    store_id: str
    items: list[OrderItem]
    amounts: OrderAmounts
    delivery_address: Address
    status: OrderStatus
    status_history: list[StatusEvent]
    payment_method: PaymentMethod
    collaborator_id: str | None
    notes: str | None
    created_at: datetime

    @classmethod
    def from_order(cls, order: Order) -> "OrderPublic":
        return cls(
            id=str(order.id),
            code=order.code,
            client_id=str(order.client_id),
            store_id=str(order.store_id),
            items=order.items,
            amounts=order.amounts,
            delivery_address=order.delivery_address,
            status=order.status,
            status_history=order.status_history,
            payment_method=order.payment_method,
            collaborator_id=str(order.collaborator_id) if order.collaborator_id else None,
            notes=order.notes,
            created_at=order.created_at,
        )
