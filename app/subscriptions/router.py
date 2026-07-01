"""Subscription endpoints (store owner). See docs/COMMISSION_AND_SUBSCRIPTION.md §6."""

from beanie import PydanticObjectId
from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.subscriptions import service
from app.subscriptions.schemas import SubscriptionPublic

router = APIRouter(tags=["subscriptions"])


@router.post("/stores/{store_id}/subscription/subscribe", response_model=SubscriptionPublic)
async def subscribe(store_id: PydanticObjectId, user: CurrentUser) -> SubscriptionPublic:
    return SubscriptionPublic.from_subscription(await service.subscribe(user, store_id))


@router.post("/stores/{store_id}/subscription/cancel", response_model=SubscriptionPublic)
async def cancel(store_id: PydanticObjectId, user: CurrentUser) -> SubscriptionPublic:
    return SubscriptionPublic.from_subscription(await service.cancel(user, store_id))


@router.get("/stores/{store_id}/subscription", response_model=SubscriptionPublic)
async def get_subscription(store_id: PydanticObjectId, user: CurrentUser) -> SubscriptionPublic:
    sub = await service.get_for_store(user, store_id)
    if sub is None:
        return SubscriptionPublic.free(str(store_id))
    return SubscriptionPublic.from_subscription(sub)
