"""Stores I/O schemas."""

from pydantic import BaseModel, Field

from app.stores.models import (
    DeliveryConfig,
    Rating,
    Schedule,
    Store,
    StoreLocation,
    StoreStatus,
)


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    location: StoreLocation
    schedule: Schedule | None = None
    delivery: DeliveryConfig | None = None
    category_ids: list[str] = Field(default_factory=list)


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None
    location: StoreLocation | None = None
    schedule: Schedule | None = None
    delivery: DeliveryConfig | None = None


class StoreStatusUpdate(BaseModel):
    status: StoreStatus


class StorePublic(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    logo_url: str | None
    cover_url: str | None
    category_ids: list[str]
    location: StoreLocation
    schedule: Schedule
    status: StoreStatus
    delivery: DeliveryConfig
    rating: Rating

    @classmethod
    def from_store(cls, store: Store) -> "StorePublic":
        return cls(
            id=str(store.id),
            owner_id=str(store.owner_id),
            name=store.name,
            description=store.description,
            logo_url=store.logo_url,
            cover_url=store.cover_url,
            category_ids=[str(cid) for cid in store.category_ids],
            location=store.location,
            schedule=store.schedule,
            status=store.status,
            delivery=store.delivery,
            rating=store.rating,
        )
