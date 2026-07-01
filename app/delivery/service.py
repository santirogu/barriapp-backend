"""Delivery business logic: assignment, status lifecycle (order sync), location, proof."""

import json
from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.collaborators import repository as collab_repo
from app.collaborators.models import Availability
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.delivery import logic
from app.delivery import repository as delivery_repo
from app.delivery.models import Delivery, DeliveryProof, DeliveryStatus, RefType
from app.delivery.schemas import DeliveryStatusUpdate, LocationUpdate, ProofUpload
from app.notifications import service as notifications_service
from app.notifications.models import NotificationType
from app.orders import repository as orders_repo
from app.orders.models import Order, OrderStatus, StatusEvent
from app.orders.models import PaymentMethod as OrderPaymentMethod
from app.stores import repository as stores_repo
from app.users.models import GeoPoint, Role, User
from app.users.service import primary_role

logger = structlog.get_logger()

COLLABORATOR_SEARCH_RADIUS_M = 5000
_MAX_ROUTE_POINTS = 500


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_admin(user: User) -> bool:
    return Role.SUPER_ADMIN in user.roles


async def _load_delivery(delivery_id: PydanticObjectId) -> Delivery:
    delivery = await delivery_repo.get_by_id(delivery_id)
    if delivery is None:
        raise AppError("Delivery not found", code="not_found", status_code=404)
    return delivery


def _record_order_status(
    order: Order, new_status: OrderStatus, by: PydanticObjectId | None
) -> None:
    order.status = new_status
    order.status_history.append(StatusEvent(status=new_status, at=_utcnow(), by=by))
    order.updated_at = _utcnow()


async def _publish(delivery: Delivery) -> None:
    payload = {
        "delivery_id": str(delivery.id),
        "status": str(delivery.status),
        "route": [p.coordinates for p in delivery.route[-1:]],
    }
    try:
        await get_redis().publish(f"delivery:{delivery.id}", json.dumps(payload))
    except Exception:
        logger.exception("delivery_publish_failed", delivery_id=str(delivery.id))


def _assert_collaborator(user: User, delivery: Delivery) -> None:
    if delivery.collaborator_id != user.id:
        raise AppError(
            "Not the assigned collaborator", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )


async def assign_order(user: User, order_id: PydanticObjectId) -> Delivery:
    order = await orders_repo.get_by_id(order_id)
    if order is None:
        raise AppError("Order not found", code="not_found", status_code=404)
    store = await stores_repo.get_by_id(order.store_id)
    if store is None or (store.owner_id != user.id and not _is_admin(user)):
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if order.status != OrderStatus.READY:
        raise AppError("Order is not ready", code="order_not_ready", status_code=409)
    if await delivery_repo.get_by_ref(RefType.ORDER, order_id) is not None:
        raise AppError("Order already assigned", code="already_assigned", status_code=409)

    candidates = await collab_repo.find_available_near(
        store.location.geo.coordinates, COLLABORATOR_SEARCH_RADIUS_M
    )
    if not candidates:
        raise AppError("No collaborator available nearby", code="no_collaborator", status_code=409)
    chosen = candidates[0]

    delivery = Delivery(ref_type=RefType.ORDER, ref_id=order.id, collaborator_id=chosen.user_id)
    await delivery_repo.insert(delivery)

    order.collaborator_id = chosen.user_id
    _record_order_status(order, OrderStatus.ASSIGNED, user.id)
    await order.save()

    chosen.availability = Availability.ON_DELIVERY
    chosen.updated_at = _utcnow()
    await chosen.save()

    await audit.record(
        module=AuditModule.DELIVERY,
        action="delivery.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="delivery",
        target_id=delivery.id,
        changes={"order_id": str(order.id), "collaborator_id": str(chosen.user_id)},
    )
    return delivery


async def advance_status(
    user: User, delivery_id: PydanticObjectId, data: DeliveryStatusUpdate
) -> Delivery:
    delivery = await _load_delivery(delivery_id)
    _assert_collaborator(user, delivery)
    if logic.next_delivery_status(delivery.status) != data.status:
        raise AppError(
            f"Cannot move from {delivery.status} to {data.status}",
            code="invalid_transition",
            status_code=409,
        )

    delivery.status = data.status
    if data.status == DeliveryStatus.PICKED_UP:
        delivery.picked_up_at = _utcnow()
    elif data.status == DeliveryStatus.DELIVERED:
        delivery.delivered_at = _utcnow()
    delivery.updated_at = _utcnow()
    await delivery.save()

    order_status = logic.order_status_for(data.status)
    if order_status is not None and delivery.ref_type == RefType.ORDER:
        order = await orders_repo.get_by_id(delivery.ref_id)
        if order is not None:
            _record_order_status(order, order_status, user.id)
            await order.save()
            # On cash delivery, settle the payment and write the ledger.
            if (
                data.status == DeliveryStatus.DELIVERED
                and order.payment_method == OrderPaymentMethod.CASH
            ):
                from app.payments import service as payments_service

                await payments_service.settle_order_payment(order)
            await notifications_service.notify(
                user_id=order.client_id,
                type=NotificationType.DELIVERY_UPDATE,
                title="Actualización de entrega",
                body=f"Tu pedido {order.code} está {order_status.value}.",
                data={"order_id": str(order.id), "status": order_status.value},
            )

    if data.status == DeliveryStatus.DELIVERED:
        assert user.id is not None
        profile = await collab_repo.get_by_user_id(user.id)
        if profile is not None and profile.availability == Availability.ON_DELIVERY:
            profile.availability = Availability.ONLINE
            profile.updated_at = _utcnow()
            await profile.save()

    await audit.record(
        module=AuditModule.DELIVERY,
        action="delivery.status.changed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="delivery",
        target_id=delivery.id,
        changes={"after": str(data.status)},
    )
    await _publish(delivery)
    return delivery


async def update_location(
    user: User, delivery_id: PydanticObjectId, data: LocationUpdate
) -> Delivery:
    delivery = await _load_delivery(delivery_id)
    _assert_collaborator(user, delivery)

    point = GeoPoint(coordinates=(data.lng, data.lat))
    delivery.route.append(point)
    if len(delivery.route) > _MAX_ROUTE_POINTS:
        delivery.route = delivery.route[-_MAX_ROUTE_POINTS:]
    delivery.updated_at = _utcnow()
    await delivery.save()

    assert user.id is not None
    profile = await collab_repo.get_by_user_id(user.id)
    if profile is not None:
        profile.current_location = point
        profile.updated_at = _utcnow()
        await profile.save()

    await _publish(delivery)
    return delivery


async def upload_proof(user: User, delivery_id: PydanticObjectId, data: ProofUpload) -> Delivery:
    delivery = await _load_delivery(delivery_id)
    _assert_collaborator(user, delivery)
    if delivery.status not in (DeliveryStatus.EN_ROUTE_DROPOFF, DeliveryStatus.DELIVERED):
        raise AppError(
            "Proof can only be uploaded near/after drop-off",
            code="invalid_transition",
            status_code=409,
        )
    delivery.proof = DeliveryProof(
        photo_url=data.photo_url, signature_url=data.signature_url, received_by=data.received_by
    )
    delivery.updated_at = _utcnow()
    await delivery.save()
    await audit.record(
        module=AuditModule.DELIVERY,
        action="delivery.proof.uploaded",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="delivery",
        target_id=delivery.id,
    )
    return delivery


async def get_delivery(user: User, delivery_id: PydanticObjectId) -> Delivery:
    delivery = await _load_delivery(delivery_id)
    if _is_admin(user) or delivery.collaborator_id == user.id:
        return delivery
    if delivery.ref_type == RefType.ORDER:
        order = await orders_repo.get_by_id(delivery.ref_id)
        if order is not None:
            if order.client_id == user.id:
                return delivery
            store = await stores_repo.get_by_id(order.store_id)
            if store is not None and store.owner_id == user.id:
                return delivery
    raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)


async def list_jobs(user: User, *, skip: int, limit: int) -> list[Delivery]:
    assert user.id is not None
    return await delivery_repo.list_by_collaborator(user.id, skip=skip, limit=limit)
