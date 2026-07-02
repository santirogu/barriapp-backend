"""Admin business logic: metrics, user moderation, audit access, platform config."""

from typing import Any

from beanie import PydanticObjectId

from app.admin.models import PlatformConfig
from app.admin.schemas import ConfigUpdate, MetricsResponse, UserStatusUpdate
from app.audit import service as audit
from app.audit.models import AuditLog, AuditModule
from app.collaborators.models import Availability, CollaboratorProfile
from app.core.errors import AppError
from app.errands.models import Errand
from app.orders.models import Order, OrderStatus
from app.payments.models import LedgerEntry, LedgerType
from app.stores.models import Store, StoreStatus
from app.users import repository as users_repo
from app.users.models import Role, User, UserStatus
from app.users.service import primary_role


async def _sum(model: type[Any], match: dict[str, Any], field: str) -> int:
    pipeline = [{"$match": match}, {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}]
    rows: list[dict[str, Any]] = await model.aggregate(pipeline).to_list()
    return int(rows[0]["total"]) if rows else 0


async def metrics() -> MetricsResponse:
    return MetricsResponse(
        users=await User.count(),
        stores=await Store.count(),
        open_stores=await Store.find(Store.status == StoreStatus.OPEN).count(),
        active_collaborators=await CollaboratorProfile.find(
            CollaboratorProfile.availability == Availability.ONLINE
        ).count(),
        orders_total=await Order.count(),
        orders_delivered=await Order.find(Order.status == OrderStatus.DELIVERED).count(),
        errands_total=await Errand.count(),
        gmv=await _sum(Order, {"status": OrderStatus.DELIVERED.value}, "amounts.total"),
        platform_revenue=await _sum(LedgerEntry, {"type": LedgerType.COMMISSION.value}, "amount"),
    )


async def list_users(
    *,
    role: Role | None,
    user_status: UserStatus | None,
    query: str | None,
    skip: int,
    limit: int,
) -> list[User]:
    criteria: dict[str, Any] = {}
    if role is not None:
        criteria["role"] = role.value
    if user_status is not None:
        criteria["status"] = user_status.value
    if query:
        criteria["$or"] = [
            {"phone": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}},
        ]
    return await User.find(criteria).skip(skip).limit(limit).to_list()


async def set_user_status(admin: User, user_id: PydanticObjectId, data: UserStatusUpdate) -> User:
    user = await users_repo.get_by_id(user_id)
    if user is None:
        raise AppError("User not found", code="not_found", status_code=404)
    previous = user.status
    user.status = data.status
    await user.save()
    action = "user.suspended" if data.status == UserStatus.SUSPENDED else "user.activated"
    await audit.record(
        module=AuditModule.USERS,
        action=action,
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="user",
        target_id=user_id,
        changes={"before": str(previous), "after": str(data.status)},
    )
    return user


async def search_audit_logs(
    admin: User,
    *,
    module: AuditModule | None,
    action: str | None,
    actor_id: PydanticObjectId | None,
    result: str | None,
    skip: int,
    limit: int,
) -> list[AuditLog]:
    criteria: dict[str, Any] = {}
    if module is not None:
        criteria["module"] = module.value
    if action:
        criteria["action"] = action
    if actor_id is not None:
        criteria["actor_id"] = actor_id
    if result:
        criteria["result"] = result
    logs = await AuditLog.find(criteria).sort("-created_at").skip(skip).limit(limit).to_list()
    await audit.record(
        module=AuditModule.ADMIN,
        action="admin.audit.read",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        changes={"filters": {k: str(v) for k, v in criteria.items()}},
    )
    return logs


async def get_audit_log(admin: User, log_id: PydanticObjectId) -> AuditLog:
    log = await AuditLog.get(log_id)
    if log is None:
        raise AppError("Audit log not found", code="not_found", status_code=404)
    await audit.record(
        module=AuditModule.ADMIN,
        action="admin.audit.read",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="audit_log",
        target_id=log_id,
    )
    return log


async def get_config() -> PlatformConfig:
    cfg = await PlatformConfig.find_one({})
    if cfg is None:
        cfg = PlatformConfig()
        await cfg.insert()
    return cfg


async def update_config(admin: User, data: ConfigUpdate) -> PlatformConfig:
    cfg = await get_config()
    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        setattr(cfg, field, value)
    await cfg.save()
    await audit.record(
        module=AuditModule.ADMIN,
        action="admin.config.updated",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="platform_config",
        changes={"updated_fields": sorted(fields)},
    )
    return cfg
