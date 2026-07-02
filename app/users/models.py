"""User identity model (Beanie) and embedded sub-documents.

See docs/DATA_MODEL.md §3.1. One account holds exactly one role (1:1): a person
who wants a second role registers a separate account. Role-specific profiles
(stores, collaborator_profiles) are separate and added by their own modules.
"""

from datetime import UTC, date, datetime
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


class DocumentType(StrEnum):
    """Colombian identity document types."""

    CC = "CC"  # Cédula de ciudadanía
    CE = "CE"  # Cédula de extranjería
    PA = "PA"  # Pasaporte
    NIT = "NIT"  # Business tax id (sellers)


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


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
    # Exactly one role per account, chosen at registration (super_admin excluded).
    role: Role
    # phone/password are optional: social-login accounts have neither at first.
    phone: str | None = None
    email: EmailStr | None = None
    password_hash: str | None = None
    first_name: str
    last_name: str
    # Identity document. Nullable at the model level because social-login accounts
    # complete these later; the registration schemas require them per role.
    # The same document may repeat across accounts (one person, one account per role).
    document_type: DocumentType | None = None
    document_number: str | None = None
    # Required for client/collaborator (18+), not collected for sellers.
    gender: Gender | None = None
    birth_date: date | None = None
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
        # phone/email are the login identifiers and stay globally unique;
        # document_number is intentionally NOT unique (repeats across role accounts).
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
            IndexModel("role"),
        ]
