"""Free errand ("mandado") model. See docs/DATA_MODEL.md §3.7 and docs/ERRAND_FLOW.md."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.users.models import Address


class ErrandStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ErrandStatusEvent(BaseModel):
    status: ErrandStatus
    at: datetime
    by: PydanticObjectId | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Errand(Document):
    code: str  # human-readable, e.g. "MD-1A2B3C4D"
    client_id: PydanticObjectId
    title: str
    description: str | None = None
    photo_url: str | None = None
    pickup: Address | None = None  # some errands have no fixed origin
    dropoff: Address
    offered_fee: int  # COP — the collaborator's earning
    estimated_cost: int | None = None  # COP — purchase reimbursement estimate
    status: ErrandStatus = ErrandStatus.OPEN
    status_history: list[ErrandStatusEvent] = Field(default_factory=list)
    collaborator_id: PydanticObjectId | None = None
    payment_id: PydanticObjectId | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "errands"
        indexes = [  # noqa: RUF012
            IndexModel("code", unique=True),
            IndexModel("client_id"),
            IndexModel("collaborator_id"),
            IndexModel([("status", 1), ("created_at", -1)]),
            IndexModel([("dropoff.geo", "2dsphere")]),
        ]
