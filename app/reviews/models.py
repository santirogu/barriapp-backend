"""Review model. See docs/DATA_MODEL.md §3.11."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class ReviewTargetType(StrEnum):
    STORE = "store"
    COLLABORATOR = "collaborator"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Review(Document):
    from_user_id: PydanticObjectId
    target_type: ReviewTargetType
    target_id: PydanticObjectId  # store id, or collaborator's user id
    order_id: PydanticObjectId | None = None
    stars: int  # 1..5
    comment: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "reviews"
        indexes = [  # noqa: RUF012
            IndexModel([("target_type", 1), ("target_id", 1), ("created_at", -1)]),
            IndexModel("from_user_id"),
        ]
