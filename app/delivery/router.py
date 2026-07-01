"""Delivery endpoints. See docs/API_CONTRACT.md §8/§9 and docs/ORDER_FLOW.md.

Live tracking over WebSocket (`/ws/deliveries/{id}`) is planned next; location
updates already publish to Redis (`delivery:{id}`) for it to consume.
"""

from beanie import PydanticObjectId
from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.delivery import service
from app.delivery.schemas import (
    DeliveryPublic,
    DeliveryStatusUpdate,
    LocationUpdate,
    ProofUpload,
)

router = APIRouter(tags=["delivery"])


@router.post(
    "/orders/{order_id}/assign", response_model=DeliveryPublic, status_code=status.HTTP_201_CREATED
)
async def assign_order(order_id: PydanticObjectId, user: CurrentUser) -> DeliveryPublic:
    return DeliveryPublic.from_delivery(await service.assign_order(user, order_id))


@router.get("/collaborator/jobs", response_model=list[DeliveryPublic])
async def list_jobs(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[DeliveryPublic]:
    jobs = await service.list_jobs(user, skip=(page - 1) * limit, limit=limit)
    return [DeliveryPublic.from_delivery(d) for d in jobs]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryPublic)
async def get_delivery(delivery_id: PydanticObjectId, user: CurrentUser) -> DeliveryPublic:
    return DeliveryPublic.from_delivery(await service.get_delivery(user, delivery_id))


@router.post("/deliveries/{delivery_id}/status", response_model=DeliveryPublic)
async def advance_status(
    delivery_id: PydanticObjectId, data: DeliveryStatusUpdate, user: CurrentUser
) -> DeliveryPublic:
    return DeliveryPublic.from_delivery(await service.advance_status(user, delivery_id, data))


@router.post("/deliveries/{delivery_id}/location", response_model=DeliveryPublic)
async def update_location(
    delivery_id: PydanticObjectId, data: LocationUpdate, user: CurrentUser
) -> DeliveryPublic:
    return DeliveryPublic.from_delivery(await service.update_location(user, delivery_id, data))


@router.post("/deliveries/{delivery_id}/proof", response_model=DeliveryPublic)
async def upload_proof(
    delivery_id: PydanticObjectId, data: ProofUpload, user: CurrentUser
) -> DeliveryPublic:
    return DeliveryPublic.from_delivery(await service.upload_proof(user, delivery_id, data))
