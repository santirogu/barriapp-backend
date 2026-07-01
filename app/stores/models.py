"""Store (seller profile) model. See docs/DATA_MODEL.md §3.2."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.users.models import GeoPoint


class StoreStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    SUSPENDED = "suspended"


class ScheduleBlock(BaseModel):
    open: str  # "HH:MM"
    close: str  # "HH:MM"


class Schedule(BaseModel):
    timezone: str = "America/Bogota"
    # weekday key ("mon".."sun") -> list of open/close blocks
    days: dict[str, list[ScheduleBlock]] = Field(default_factory=dict)


class DeliveryConfig(BaseModel):
    radius_meters: int = 2000
    base_fee: int = 0  # COP
    min_order: int = 0  # COP
    free_over: int | None = None  # COP threshold for free delivery


class StoreLocation(BaseModel):
    line: str
    city: str | None = None
    geo: GeoPoint


class Rating(BaseModel):
    avg: float = 0.0
    count: int = 0


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Store(Document):
    owner_id: PydanticObjectId
    name: str
    description: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    category_ids: list[PydanticObjectId] = Field(default_factory=list)
    location: StoreLocation
    schedule: Schedule = Field(default_factory=Schedule)
    status: StoreStatus = StoreStatus.CLOSED
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    commission_rate: float | None = None  # per-store override of the global default
    rating: Rating = Field(default_factory=Rating)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "stores"
        indexes = [  # noqa: RUF012
            IndexModel([("location.geo", "2dsphere")]),
            IndexModel("owner_id"),
            IndexModel("status"),
        ]
