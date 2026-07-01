"""Data access for deliveries."""

from beanie import PydanticObjectId

from app.delivery.models import Delivery, RefType


async def get_by_id(delivery_id: PydanticObjectId) -> Delivery | None:
    return await Delivery.get(delivery_id)


async def insert(delivery: Delivery) -> Delivery:
    return await delivery.insert()


async def get_by_ref(ref_type: RefType, ref_id: PydanticObjectId) -> Delivery | None:
    return await Delivery.find_one(Delivery.ref_type == ref_type, Delivery.ref_id == ref_id)


async def list_by_collaborator(
    collaborator_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Delivery]:
    return (
        await Delivery.find(Delivery.collaborator_id == collaborator_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
