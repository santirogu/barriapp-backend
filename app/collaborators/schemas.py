"""Collaborators I/O schemas."""

from pydantic import BaseModel, Field

from app.collaborators.models import (
    Availability,
    CollaboratorDocuments,
    CollaboratorProfile,
    Rating,
    VehicleType,
    VerificationStatus,
)


class BecomeCollaborator(BaseModel):
    vehicle_type: VehicleType
    id_number: str = Field(min_length=3, max_length=30)
    license_url: str | None = None


class AvailabilityUpdate(BaseModel):
    status: Availability  # only `online` / `offline` are accepted from the collaborator
    lng: float | None = None
    lat: float | None = None


class VerificationUpdate(BaseModel):
    status: VerificationStatus
    reason: str | None = None


class CollaboratorProfilePublic(BaseModel):
    id: str
    user_id: str
    vehicle_type: VehicleType
    documents: CollaboratorDocuments
    verification_status: VerificationStatus
    availability: Availability
    rating: Rating
    balance: int

    @classmethod
    def from_profile(cls, profile: CollaboratorProfile) -> "CollaboratorProfilePublic":
        return cls(
            id=str(profile.id),
            user_id=str(profile.user_id),
            vehicle_type=profile.vehicle_type,
            documents=profile.documents,
            verification_status=profile.verification_status,
            availability=profile.availability,
            rating=profile.rating,
            balance=profile.balance,
        )
