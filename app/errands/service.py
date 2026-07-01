"""Errands business logic: publish, browse, accept, advance, cancel (cash-only)."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.errors import AppError
from app.errands import logic
from app.errands import repository as errands_repo
from app.errands.models import Errand, ErrandStatus, ErrandStatusEvent
from app.errands.schemas import ErrandCancel, ErrandCreate, ErrandStatusUpdate
from app.payments import service as payments_service
from app.users.models import Role, User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_admin(user: User) -> bool:
    return Role.SUPER_ADMIN in user.roles


def _record_status(errand: Errand, new_status: ErrandStatus, by: PydanticObjectId | None) -> None:
    errand.status = new_status
    errand.status_history.append(ErrandStatusEvent(status=new_status, at=_utcnow(), by=by))
    errand.updated_at = _utcnow()


async def _load(errand_id: PydanticObjectId) -> Errand:
    errand = await errands_repo.get_by_id(errand_id)
    if errand is None:
        raise AppError("Errand not found", code="not_found", status_code=404)
    return errand


async def create_errand(user: User, data: ErrandCreate) -> Errand:
    errand = Errand(
        code=logic.generate_errand_code(),
        client_id=user.id,
        title=data.title,
        description=data.description,
        photo_url=data.photo_url,
        pickup=data.pickup,
        dropoff=data.dropoff,
        offered_fee=data.offered_fee,
        estimated_cost=data.estimated_cost,
    )
    _record_status(errand, ErrandStatus.OPEN, user.id)
    await errands_repo.insert(errand)
    await audit.record(
        module=AuditModule.ERRANDS,
        action="errand.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="errand",
        target_id=errand.id,
    )
    return errand


async def list_mine(user: User, *, skip: int, limit: int) -> list[Errand]:
    assert user.id is not None
    return await errands_repo.list_by_client(user.id, skip=skip, limit=limit)


async def list_assigned(user: User, *, skip: int, limit: int) -> list[Errand]:
    """Errands the caller accepted as a collaborator (to track/advance them)."""
    assert user.id is not None
    return await errands_repo.list_by_collaborator(user.id, skip=skip, limit=limit)


async def get_errand(user: User, errand_id: PydanticObjectId) -> Errand:
    errand = await _load(errand_id)
    if _is_admin(user) or user.id in (errand.client_id, errand.collaborator_id):
        return errand
    raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)


async def search_available(near: tuple[float, float], radius_meters: int) -> list[Errand]:
    return await errands_repo.search_available_near(near, radius_meters)


async def accept(user: User, errand_id: PydanticObjectId) -> Errand:
    if Role.COLLABORATOR not in user.roles:
        raise AppError(
            "Only approved collaborators can accept errands",
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    errand = await _load(errand_id)
    if errand.status != ErrandStatus.OPEN:
        raise AppError("Errand is not open", code="invalid_transition", status_code=409)
    errand.collaborator_id = user.id
    _record_status(errand, ErrandStatus.ASSIGNED, user.id)
    await errand.save()
    await audit.record(
        module=AuditModule.ERRANDS,
        action="errand.accepted",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="errand",
        target_id=errand.id,
    )
    return errand


async def advance_status(
    user: User, errand_id: PydanticObjectId, data: ErrandStatusUpdate
) -> Errand:
    errand = await _load(errand_id)
    if errand.collaborator_id != user.id:
        raise AppError(
            "Not the assigned collaborator", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )
    if logic.next_status(errand.status) != data.status:
        raise AppError(
            f"Cannot move from {errand.status} to {data.status}",
            code="invalid_transition",
            status_code=409,
        )
    _record_status(errand, data.status, user.id)
    await errand.save()

    if data.status == ErrandStatus.COMPLETED:
        assert errand.id is not None
        payment = await payments_service.settle_errand_payment(
            errand_id=errand.id,
            client_id=errand.client_id,
            collaborator_id=errand.collaborator_id,
            offered_fee=errand.offered_fee,
        )
        if payment is not None:
            errand.payment_id = payment.id
            await errand.save()

    await audit.record(
        module=AuditModule.ERRANDS,
        action="errand.status.changed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="errand",
        target_id=errand.id,
        changes={"after": str(data.status)},
    )
    return errand


async def cancel(user: User, errand_id: PydanticObjectId, data: ErrandCancel) -> Errand:
    errand = await _load(errand_id)
    if errand.client_id != user.id and not _is_admin(user):
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if not logic.can_cancel(errand.status):
        raise AppError(
            f"Errand in status {errand.status} cannot be cancelled",
            code="invalid_transition",
            status_code=409,
        )
    _record_status(errand, ErrandStatus.CANCELLED, user.id)
    await errand.save()
    await audit.record(
        module=AuditModule.ERRANDS,
        action="errand.cancelled",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="errand",
        target_id=errand.id,
        changes={"reason": data.reason},
    )
    return errand
