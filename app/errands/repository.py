"""Data access for errands (incl. geospatial availability search)."""

from beanie import PydanticObjectId

from app.errands import logic
from app.errands.models import Errand


async def get_by_id(errand_id: PydanticObjectId) -> Errand | None:
    return await Errand.get(errand_id)


async def insert(errand: Errand) -> Errand:
    return await errand.insert()


async def list_by_client(
    client_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Errand]:
    return (
        await Errand.find(Errand.client_id == client_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def list_by_collaborator(
    collaborator_id: PydanticObjectId, *, skip: int = 0, limit: int = 20
) -> list[Errand]:
    return (
        await Errand.find(Errand.collaborator_id == collaborator_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def search_available_near(
    near: tuple[float, float], radius_meters: int, *, limit: int = 20
) -> list[Errand]:
    return (
        await Errand.find(logic.build_available_query(near, radius_meters)).limit(limit).to_list()
    )
