"""Reviews endpoints. See docs/API_CONTRACT.md §11."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.reviews import service
from app.reviews.schemas import ReviewCreate, ReviewPublic

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
async def create_review(data: ReviewCreate, user: CurrentUser) -> ReviewPublic:
    return ReviewPublic.from_review(await service.create_review(user, data))


@router.get("/stores/{store_id}/reviews", response_model=list[ReviewPublic])
async def list_store_reviews(
    store_id: PydanticObjectId,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[ReviewPublic]:
    reviews = await service.list_store_reviews(store_id, skip=(page - 1) * limit, limit=limit)
    return [ReviewPublic.from_review(r) for r in reviews]
