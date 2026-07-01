"""Reviews I/O schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.reviews.models import Review, ReviewTargetType


class ReviewCreate(BaseModel):
    order_id: str
    target_type: ReviewTargetType
    stars: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewPublic(BaseModel):
    id: str
    from_user_id: str
    target_type: ReviewTargetType
    target_id: str
    order_id: str | None
    stars: int
    comment: str | None
    created_at: datetime

    @classmethod
    def from_review(cls, review: Review) -> "ReviewPublic":
        return cls(
            id=str(review.id),
            from_user_id=str(review.from_user_id),
            target_type=review.target_type,
            target_id=str(review.target_id),
            order_id=str(review.order_id) if review.order_id else None,
            stars=review.stars,
            comment=review.comment,
            created_at=review.created_at,
        )
