"""Order model and embedded sub-documents. See docs/DATA_MODEL.md §3.6."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.users.models import Address


class OrderStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"
    WOMPI = "wompi"


class OrderItem(BaseModel):
    """Immutable snapshot of a purchased product at order time."""

    product_id: PydanticObjectId
    name: str
    price: int  # COP, snapshot
    qty: int
    subtotal: int  # price * qty


class OrderAmounts(BaseModel):
    items_total: int
    delivery_fee: int
    platform_fee: int  # platform commission withheld from the seller
    discount: int
    total: int  # what the client pays: items_total + delivery_fee - discount


class StatusEvent(BaseModel):
    status: OrderStatus
    at: datetime
    by: PydanticObjectId | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Order(Document):
    code: str  # human-readable, e.g. "BA-1A2B3C4D"
    client_id: PydanticObjectId
    store_id: PydanticObjectId
    items: list[OrderItem]
    amounts: OrderAmounts
    delivery_address: Address
    status: OrderStatus = OrderStatus.PENDING
    status_history: list[StatusEvent] = Field(default_factory=list)
    payment_method: PaymentMethod
    payment_id: PydanticObjectId | None = None
    collaborator_id: PydanticObjectId | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "orders"
        indexes = [  # noqa: RUF012
            IndexModel("code", unique=True),
            IndexModel("client_id"),
            IndexModel("store_id"),
            IndexModel("collaborator_id"),
            IndexModel([("status", 1), ("created_at", -1)]),
        ]
