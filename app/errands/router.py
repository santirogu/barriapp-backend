"""Errand endpoints. See docs/API_CONTRACT.md §7 and docs/ERRAND_FLOW.md."""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.errands import service
from app.errands.schemas import (
    ErrandCancel,
    ErrandCreate,
    ErrandPublic,
    ErrandStatusUpdate,
)

router = APIRouter(prefix="/errands", tags=["errands"])


def _parse_near(near: str) -> tuple[float, float]:
    parts = near.split(",")
    if len(parts) != 2:
        raise AppError("near must be 'lng,lat'", code="invalid_query", status_code=422)
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise AppError("near must be 'lng,lat'", code="invalid_query", status_code=422) from exc


@router.post("", response_model=ErrandPublic, status_code=status.HTTP_201_CREATED)
async def create_errand(data: ErrandCreate, user: CurrentUser) -> ErrandPublic:
    return ErrandPublic.from_errand(await service.create_errand(user, data))


@router.get("", response_model=list[ErrandPublic])
async def list_mine(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[ErrandPublic]:
    errands = await service.list_mine(user, skip=(page - 1) * limit, limit=limit)
    return [ErrandPublic.from_errand(e) for e in errands]


@router.get("/available", response_model=list[ErrandPublic])
async def list_available(
    user: CurrentUser,
    near: str = Query(..., description="'lng,lat'"),
    radius: int = Query(5000, ge=1, le=50000),
) -> list[ErrandPublic]:
    errands = await service.search_available(_parse_near(near), radius)
    return [ErrandPublic.from_errand(e) for e in errands]


@router.get("/{errand_id}", response_model=ErrandPublic)
async def get_errand(errand_id: PydanticObjectId, user: CurrentUser) -> ErrandPublic:
    return ErrandPublic.from_errand(await service.get_errand(user, errand_id))


@router.post("/{errand_id}/accept", response_model=ErrandPublic)
async def accept_errand(errand_id: PydanticObjectId, user: CurrentUser) -> ErrandPublic:
    return ErrandPublic.from_errand(await service.accept(user, errand_id))


@router.post("/{errand_id}/status", response_model=ErrandPublic)
async def advance_status(
    errand_id: PydanticObjectId, data: ErrandStatusUpdate, user: CurrentUser
) -> ErrandPublic:
    return ErrandPublic.from_errand(await service.advance_status(user, errand_id, data))


@router.post("/{errand_id}/cancel", response_model=ErrandPublic)
async def cancel_errand(
    errand_id: PydanticObjectId, data: ErrandCancel, user: CurrentUser
) -> ErrandPublic:
    return ErrandPublic.from_errand(await service.cancel(user, errand_id, data))
