"""Errands I/O schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.errands.models import Errand, ErrandStatus, ErrandStatusEvent
from app.users.models import Address


class ErrandCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    photo_url: str | None = None
    pickup: Address | None = None
    dropoff: Address
    offered_fee: int = Field(ge=1)
    estimated_cost: int | None = Field(default=None, ge=0)


class ErrandStatusUpdate(BaseModel):
    status: ErrandStatus


class ErrandCancel(BaseModel):
    reason: str | None = None


class ErrandPublic(BaseModel):
    id: str
    code: str
    client_id: str
    title: str
    description: str | None
    photo_url: str | None
    pickup: Address | None
    dropoff: Address
    offered_fee: int
    estimated_cost: int | None
    status: ErrandStatus
    status_history: list[ErrandStatusEvent]
    collaborator_id: str | None
    created_at: datetime

    @classmethod
    def from_errand(cls, errand: Errand) -> "ErrandPublic":
        return cls(
            id=str(errand.id),
            code=errand.code,
            client_id=str(errand.client_id),
            title=errand.title,
            description=errand.description,
            photo_url=errand.photo_url,
            pickup=errand.pickup,
            dropoff=errand.dropoff,
            offered_fee=errand.offered_fee,
            estimated_cost=errand.estimated_cost,
            status=errand.status,
            status_history=errand.status_history,
            collaborator_id=str(errand.collaborator_id) if errand.collaborator_id else None,
            created_at=errand.created_at,
        )
