"""Data access for reviews."""

from beanie import PydanticObjectId

from app.reviews.models import Review, ReviewTargetType


async def insert(review: Review) -> Review:
    return await review.insert()


async def get_existing(
    from_user_id: PydanticObjectId,
    target_type: ReviewTargetType,
    target_id: PydanticObjectId,
    order_id: PydanticObjectId,
) -> Review | None:
    return await Review.find_one(
        Review.from_user_id == from_user_id,
        Review.target_type == target_type,
        Review.target_id == target_id,
        Review.order_id == order_id,
    )


async def list_by_target(
    target_type: ReviewTargetType, target_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Review]:
    return (
        await Review.find(Review.target_type == target_type, Review.target_id == target_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
