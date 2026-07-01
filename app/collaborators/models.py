"""Collaborator profile model. See docs/DATA_MODEL.md §3.3 and
docs/COLLABORATOR_ONBOARDING.md."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.users.models import GeoPoint


class VehicleType(StrEnum):
    WALK = "walk"
    BIKE = "bike"
    MOTORCYCLE = "motorcycle"
    CAR = "car"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    NEEDS_MORE_INFO = "needs_more_info"
    APPROVED = "approved"
    REJECTED = "rejected"


class Availability(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"
    ON_DELIVERY = "on_delivery"


class CollaboratorDocuments(BaseModel):
    id_number: str
    license_url: str | None = None


class Rating(BaseModel):
    avg: float = 0.0
    count: int = 0


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CollaboratorProfile(Document):
    user_id: PydanticObjectId
    vehicle_type: VehicleType
    documents: CollaboratorDocuments
    verification_status: VerificationStatus = VerificationStatus.PENDING
    availability: Availability = Availability.OFFLINE
    current_location: GeoPoint | None = None
    rating: Rating = Field(default_factory=Rating)
    balance: int = 0  # COP, pending payout
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "collaborator_profiles"
        indexes = [  # noqa: RUF012
            IndexModel("user_id", unique=True),
            IndexModel([("current_location", "2dsphere")]),
            IndexModel("availability"),
            IndexModel("verification_status"),
        ]
