"""Stores business logic: onboarding, retrieval, geo search, updates, status."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.errors import AppError
from app.stores import repository as stores_repo
from app.stores.models import DeliveryConfig, Schedule, Store, StoreStatus
from app.stores.schemas import StoreCreate, StoreStatusUpdate, StoreUpdate
from app.users.models import Role, User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_admin(user: User) -> bool:
    return user.role == Role.SUPER_ADMIN


async def _load_owned_store(user: User, store_id: PydanticObjectId) -> Store:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
    if store.owner_id != user.id and not _is_admin(user):
        raise AppError(
            "Not the store owner", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )
    return store


async def create_store(user: User, data: StoreCreate) -> Store:
    # Role is fixed at registration: only sellers own stores.
    if user.role != Role.SELLER:
        raise AppError(
            "Only sellers can create stores",
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    store = Store(
        owner_id=user.id,
        name=data.name,
        description=data.description,
        location=data.location,
        schedule=data.schedule or Schedule(),
        delivery=data.delivery or DeliveryConfig(),
        category_ids=[PydanticObjectId(cid) for cid in data.category_ids],
    )
    await stores_repo.insert(store)
    await audit.record(
        module=AuditModule.STORES,
        action="store.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="store",
        target_id=store.id,
    )
    return store


async def get_store(store_id: PydanticObjectId) -> Store:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
    return store


async def list_my_stores(user: User) -> list[Store]:
    """Stores owned by the caller (seller area). Empty if not a seller yet."""
    assert user.id is not None
    return await stores_repo.list_by_owner(user.id)


async def search_stores(
    *,
    near: tuple[float, float] | None,
    radius_meters: int,
    category_id: PydanticObjectId | None,
    query: str | None,
    skip: int,
    limit: int,
) -> list[Store]:
    return await stores_repo.search(
        near=near,
        radius_meters=radius_meters,
        category_id=category_id,
        query=query,
        skip=skip,
        limit=limit,
    )


async def update_store(user: User, store_id: PydanticObjectId, data: StoreUpdate) -> Store:
    store = await _load_owned_store(user, store_id)
    fields = data.model_dump(exclude_unset=True)
    for field in fields:
        setattr(store, field, getattr(data, field))
    if fields:
        store.updated_at = _utcnow()
        await store.save()
        await audit.record(
            module=AuditModule.STORES,
            action="store.updated",
            actor_id=user.id,
            actor_role=primary_role(user),
            target_type="store",
            target_id=store.id,
            changes={"updated_fields": sorted(fields)},
        )
    return store


async def set_status(user: User, store_id: PydanticObjectId, data: StoreStatusUpdate) -> Store:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)

    # Suspension (and lifting it) is an admin-only moderation action.
    involves_suspension = StoreStatus.SUSPENDED in (data.status, store.status)
    if involves_suspension and not _is_admin(user):
        raise AppError(
            "Only an admin can (un)suspend a store",
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    if not involves_suspension and store.owner_id != user.id and not _is_admin(user):
        raise AppError(
            "Not the store owner", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )

    previous = store.status
    store.status = data.status
    store.updated_at = _utcnow()
    await store.save()
    await audit.record(
        module=AuditModule.STORES,
        action="store.status.changed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="store",
        target_id=store.id,
        changes={"before": str(previous), "after": str(data.status)},
    )
    return store
