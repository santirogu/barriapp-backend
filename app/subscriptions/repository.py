"""Data access for subscriptions."""

from beanie import PydanticObjectId

from app.subscriptions.models import Subscription


async def get_by_store(store_id: PydanticObjectId) -> Subscription | None:
    return await Subscription.find_one(Subscription.store_id == store_id)


async def insert(subscription: Subscription) -> Subscription:
    return await subscription.insert()
