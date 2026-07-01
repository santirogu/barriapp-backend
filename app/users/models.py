"""User identity model (Beanie) and embedded sub-documents.

See docs/DATA_MODEL.md §3.1. One identity per person; role-specific profiles
(stores, collaborator_profiles) are separate and added by their own modules.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from beanie import Document
from pydantic import BaseModel, EmailStr, Field
from pymongo import IndexModel


class Role(StrEnum):
    CLIENT = "client"
    SELLER = "seller"
    COLLABORATOR = "collaborator"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Consent(BaseModel):
    """Habeas Data (Ley 1581) consent record — versioned and timestamped."""

    habeas_data: bool
    version: str
    accepted_at: datetime


class GeoPoint(BaseModel):
    """GeoJSON point. Coordinates are [longitude, latitude]."""

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class Address(BaseModel):
    label: str
    line: str
    city: str | None = None
    notes: str | None = None
    geo: GeoPoint | None = None
    is_default: bool = False


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Document):
    # phone/password are optional: social-login accounts have neither.
    phone: str | None = None
    email: EmailStr | None = None
    password_hash: str | None = None
    full_name: str
    roles: list[Role] = Field(default_factory=lambda: [Role.CLIENT])
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    avatar_url: str | None = None
    addresses: list[Address] = Field(default_factory=list)
    device_tokens: list[str] = Field(default_factory=list)
    google_sub: str | None = None  # Google account subject (social login)
    apple_sub: str | None = None  # Apple account subject (social login)
    consent: Consent
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "users"
        # Partial (not sparse) unique indexes: uniqueness only among real string
        # values, so the many accounts lacking a field (null) don't collide.
        indexes = [  # noqa: RUF012
            IndexModel(
                "phone", unique=True, partialFilterExpression={"phone": {"$type": "string"}}
            ),
            IndexModel(
                "email", unique=True, partialFilterExpression={"email": {"$type": "string"}}
            ),
            IndexModel(
                "google_sub",
                unique=True,
                partialFilterExpression={"google_sub": {"$type": "string"}},
            ),
            IndexModel(
                "apple_sub", unique=True, partialFilterExpression={"apple_sub": {"$type": "string"}}
            ),
            IndexModel("roles"),
        ]
