"""Subscriptions business logic.

Premium's headline effect is a reduced commission: subscribing sets the store's
``commission_rate`` override (so the existing order commission resolution applies),
and cancelling clears it (back to the global default). Billing via Wompi recurring
is simulated for now.
"""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.config import get_settings
from app.core.errors import AppError
from app.stores import repository as stores_repo
from app.stores.models import Store
from app.subscriptions import repository as sub_repo
from app.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
from app.users.models import Role, User
from app.users.service import primary_role

_RENEWAL_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _owned_store(user: User, store_id: PydanticObjectId) -> Store:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=404)
    if store.owner_id != user.id and user.role != Role.SUPER_ADMIN:
        raise AppError(
            "Not the store owner", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )
    return store


async def subscribe(user: User, store_id: PydanticObjectId) -> Subscription:
    store = await _owned_store(user, store_id)
    settings = get_settings()
    now = _utcnow()
    renews_at = now + timedelta(days=_RENEWAL_DAYS)

    sub = await sub_repo.get_by_store(store_id)
    if sub is None:
        sub = Subscription(
            store_id=store_id,
            plan=SubscriptionPlan.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            commission_rate=settings.premium_commission_rate,
            price=settings.subscription_price,
            started_at=now,
            renews_at=renews_at,
        )
        await sub_repo.insert(sub)
    else:
        sub.plan = SubscriptionPlan.PREMIUM
        sub.status = SubscriptionStatus.ACTIVE
        sub.commission_rate = settings.premium_commission_rate
        sub.price = settings.subscription_price
        sub.renews_at = renews_at
        sub.updated_at = now
        await sub.save()

    # Apply the reduced commission to the store.
    store.commission_rate = settings.premium_commission_rate
    store.updated_at = now
    await store.save()

    await audit.record(
        module=AuditModule.PAYMENTS,
        action="subscription.activated",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="store",
        target_id=store_id,
        changes={"commission_rate": settings.premium_commission_rate},
    )
    return sub


async def cancel(user: User, store_id: PydanticObjectId) -> Subscription:
    store = await _owned_store(user, store_id)
    sub = await sub_repo.get_by_store(store_id)
    if sub is None or sub.status != SubscriptionStatus.ACTIVE:
        raise AppError("No active subscription", code="no_active_subscription", status_code=409)
    now = _utcnow()
    sub.status = SubscriptionStatus.CANCELLED
    sub.updated_at = now
    await sub.save()

    # Revert to the global default commission.
    store.commission_rate = None
    store.updated_at = now
    await store.save()

    await audit.record(
        module=AuditModule.PAYMENTS,
        action="subscription.cancelled",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="store",
        target_id=store_id,
    )
    return sub


async def get_for_store(user: User, store_id: PydanticObjectId) -> Subscription | None:
    await _owned_store(user, store_id)
    return await sub_repo.get_by_store(store_id)
