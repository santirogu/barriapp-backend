"""Delivery model (polymorphic over orders/errands). See docs/DATA_MODEL.md §3.8."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.users.models import GeoPoint


class RefType(StrEnum):
    ORDER = "order"
    ERRAND = "errand"


class DeliveryStatus(StrEnum):
    ASSIGNED = "assigned"
    EN_ROUTE_PICKUP = "en_route_pickup"
    PICKED_UP = "picked_up"
    EN_ROUTE_DROPOFF = "en_route_dropoff"
    DELIVERED = "delivered"


class DeliveryProof(BaseModel):
    photo_url: str | None = None
    signature_url: str | None = None
    received_by: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Delivery(Document):
    ref_type: RefType
    ref_id: PydanticObjectId  # points to an order or errand
    collaborator_id: PydanticObjectId  # the collaborator's user id
    status: DeliveryStatus = DeliveryStatus.ASSIGNED
    route: list[GeoPoint] = Field(default_factory=list)  # sampled breadcrumbs
    proof: DeliveryProof | None = None
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "deliveries"
        indexes = [  # noqa: RUF012
            IndexModel([("ref_type", 1), ("ref_id", 1)]),
            IndexModel("collaborator_id"),
            IndexModel("status"),
        ]
