"""Stores endpoints. See docs/API_CONTRACT.md §3."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.stores import service
from app.stores.schemas import StoreCreate, StorePublic, StoreStatusUpdate, StoreUpdate

router = APIRouter(tags=["stores"])


def _parse_near(near: str | None) -> tuple[float, float] | None:
    if not near:
        return None
    parts = near.split(",")
    if len(parts) != 2:
        raise AppError(
            "near must be 'lng,lat'",
            code="invalid_query",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        lng, lat = float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise AppError(
            "near must be 'lng,lat'",
            code="invalid_query",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc
    return (lng, lat)


def _parse_object_id(value: str | None, field: str) -> PydanticObjectId | None:
    if not value:
        return None
    try:
        return PydanticObjectId(value)
    except (ValueError, TypeError) as exc:
        raise AppError(
            f"Invalid {field}",
            code="invalid_query",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from exc


@router.post("/stores", response_model=StorePublic, status_code=status.HTTP_201_CREATED)
async def create_store(data: StoreCreate, user: CurrentUser) -> StorePublic:
    return StorePublic.from_store(await service.create_store(user, data))


@router.get("/stores", response_model=list[StorePublic])
async def list_stores(
    near: str | None = Query(None, description="'lng,lat'"),
    radius: int = Query(5000, ge=1, le=50000, description="meters"),
    category: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[StorePublic]:
    stores = await service.search_stores(
        near=_parse_near(near),
        radius_meters=radius,
        category_id=_parse_object_id(category, "category"),
        query=q,
        skip=(page - 1) * limit,
        limit=limit,
    )
    return [StorePublic.from_store(s) for s in stores]


@router.get("/stores/{store_id}", response_model=StorePublic)
async def get_store(store_id: PydanticObjectId) -> StorePublic:
    return StorePublic.from_store(await service.get_store(store_id))


@router.patch("/stores/{store_id}", response_model=StorePublic)
async def update_store(
    store_id: PydanticObjectId, data: StoreUpdate, user: CurrentUser
) -> StorePublic:
    return StorePublic.from_store(await service.update_store(user, store_id, data))


@router.patch("/stores/{store_id}/status", response_model=StorePublic)
async def set_store_status(
    store_id: PydanticObjectId, data: StoreStatusUpdate, user: CurrentUser
) -> StorePublic:
    return StorePublic.from_store(await service.set_status(user, store_id, data))
