"""Delivery I/O schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.delivery.models import Delivery, DeliveryProof, DeliveryStatus, RefType
from app.users.models import GeoPoint


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus


class LocationUpdate(BaseModel):
    lng: float
    lat: float


class ProofUpload(BaseModel):
    photo_url: str | None = None
    signature_url: str | None = None
    received_by: str | None = None


class DeliveryPublic(BaseModel):
    id: str
    ref_type: RefType
    ref_id: str
    collaborator_id: str
    status: DeliveryStatus
    route: list[GeoPoint]
    proof: DeliveryProof | None
    picked_up_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime

    @classmethod
    def from_delivery(cls, delivery: Delivery) -> "DeliveryPublic":
        return cls(
            id=str(delivery.id),
            ref_type=delivery.ref_type,
            ref_id=str(delivery.ref_id),
            collaborator_id=str(delivery.collaborator_id),
            status=delivery.status,
            route=delivery.route,
            proof=delivery.proof,
            picked_up_at=delivery.picked_up_at,
            delivered_at=delivery.delivered_at,
            created_at=delivery.created_at,
        )
