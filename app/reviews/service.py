"""Reviews business logic: rate a store/collaborator after a delivered order."""

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.collaborators import repository as collab_repo
from app.collaborators.models import Rating as CollabRating
from app.core.errors import AppError
from app.orders import repository as orders_repo
from app.orders.models import OrderStatus
from app.reviews import logic
from app.reviews import repository as reviews_repo
from app.reviews.models import Review, ReviewTargetType
from app.reviews.schemas import ReviewCreate
from app.stores import repository as stores_repo
from app.stores.models import Rating as StoreRating
from app.users.models import User
from app.users.service import primary_role


async def _apply_rating(
    target_type: ReviewTargetType, target_id: PydanticObjectId, stars: int
) -> None:
    if target_type == ReviewTargetType.STORE:
        store = await stores_repo.get_by_id(target_id)
        if store is not None:
            avg, count = logic.recompute_rating(store.rating.avg, store.rating.count, stars)
            store.rating = StoreRating(avg=avg, count=count)
            await store.save()
    else:
        profile = await collab_repo.get_by_user_id(target_id)
        if profile is not None:
            avg, count = logic.recompute_rating(profile.rating.avg, profile.rating.count, stars)
            profile.rating = CollabRating(avg=avg, count=count)
            await profile.save()


async def create_review(user: User, data: ReviewCreate) -> Review:
    assert user.id is not None
    order = await orders_repo.get_by_id(PydanticObjectId(data.order_id))
    if order is None:
        raise AppError("Order not found", code="not_found", status_code=404)
    if order.client_id != user.id:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if order.status != OrderStatus.DELIVERED:
        raise AppError("Can only review a delivered order", code="not_delivered", status_code=409)

    if data.target_type == ReviewTargetType.STORE:
        target_id = order.store_id
    else:
        if order.collaborator_id is None:
            raise AppError(
                "Order has no collaborator to review", code="no_collaborator", status_code=409
            )
        target_id = order.collaborator_id

    assert order.id is not None
    if await reviews_repo.get_existing(user.id, data.target_type, target_id, order.id) is not None:
        raise AppError("Already reviewed", code="already_reviewed", status_code=409)

    review = Review(
        from_user_id=user.id,
        target_type=data.target_type,
        target_id=target_id,
        order_id=order.id,
        stars=data.stars,
        comment=data.comment,
    )
    await reviews_repo.insert(review)
    await _apply_rating(data.target_type, target_id, data.stars)

    await audit.record(
        module=AuditModule.REVIEWS,
        action="review.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type=data.target_type.value,
        target_id=target_id,
        changes={"stars": data.stars},
    )
    return review


async def list_store_reviews(store_id: PydanticObjectId, *, skip: int, limit: int) -> list[Review]:
    return await reviews_repo.list_by_target(
        ReviewTargetType.STORE, store_id, skip=skip, limit=limit
    )
