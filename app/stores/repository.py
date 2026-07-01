"""Data access for stores (Beanie queries, incl. geospatial search)."""

from typing import Any

from beanie import PydanticObjectId

from app.stores.models import Store, StoreStatus


async def get_by_id(store_id: PydanticObjectId) -> Store | None:
    return await Store.get(store_id)


async def insert(store: Store) -> Store:
    return await store.insert()


async def search(
    *,
    near: tuple[float, float] | None = None,
    radius_meters: int = 5000,
    category_id: PydanticObjectId | None = None,
    query: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Store]:
    """Search stores, optionally by proximity, category, and name.

    Suspended stores are never returned. When ``near`` is given, results come back
    nearest-first via the 2dsphere index.
    """
    criteria: dict[str, Any] = {"status": {"$ne": StoreStatus.SUSPENDED.value}}
    if near is not None:
        criteria["location.geo"] = {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [near[0], near[1]]},
                "$maxDistance": radius_meters,
            }
        }
    if category_id is not None:
        criteria["category_ids"] = category_id
    if query:
        criteria["name"] = {"$regex": query, "$options": "i"}

    return await Store.find(criteria).skip(skip).limit(limit).to_list()
