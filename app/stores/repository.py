"""Data access for stores (Beanie queries, incl. geospatial search)."""

from typing import Any

from beanie import PydanticObjectId

from app.stores.models import Store, StoreStatus


async def get_by_id(store_id: PydanticObjectId) -> Store | None:
    return await Store.get(store_id)


async def insert(store: Store) -> Store:
    return await store.insert()


def build_search_criteria(
    *,
    near: tuple[float, float] | None = None,
    radius_meters: int = 5000,
    category_id: PydanticObjectId | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """Build the Mongo query for store search (pure; unit-tested separately).

    Suspended stores are always excluded. With ``near``, a 2dsphere ``$near``
    clause is added so results come back nearest-first.
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
    return criteria


async def search(
    *,
    near: tuple[float, float] | None = None,
    radius_meters: int = 5000,
    category_id: PydanticObjectId | None = None,
    query: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Store]:
    """Search stores, optionally by proximity, category, and name."""
    criteria = build_search_criteria(
        near=near, radius_meters=radius_meters, category_id=category_id, query=query
    )
    return await Store.find(criteria).skip(skip).limit(limit).to_list()
