"""Admin endpoints (super_admin only). See docs/API_CONTRACT.md §14 and
docs/ADMIN_PANEL.md."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query

from app.admin import service
from app.admin.schemas import (
    AuditLogPublic,
    ConfigPublic,
    ConfigUpdate,
    MetricsResponse,
    UserStatusUpdate,
)
from app.audit.models import AuditModule
from app.core.deps import require_roles
from app.users.models import Role, User, UserStatus
from app.users.schemas import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles(Role.SUPER_ADMIN))]


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(admin: AdminUser) -> MetricsResponse:
    return await service.metrics()


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    admin: AdminUser,
    role: Role | None = Query(None),
    user_status: UserStatus | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[UserPublic]:
    users = await service.list_users(
        role=role, user_status=user_status, query=q, skip=(page - 1) * limit, limit=limit
    )
    return [UserPublic.from_user(u) for u in users]


@router.patch("/users/{user_id}/status", response_model=UserPublic)
async def set_user_status(
    user_id: PydanticObjectId, data: UserStatusUpdate, admin: AdminUser
) -> UserPublic:
    return UserPublic.from_user(await service.set_user_status(admin, user_id, data))


@router.get("/audit-logs", response_model=list[AuditLogPublic])
async def search_audit_logs(
    admin: AdminUser,
    module: AuditModule | None = Query(None),
    action: str | None = Query(None),
    actor_id: PydanticObjectId | None = Query(None),
    result: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> list[AuditLogPublic]:
    logs = await service.search_audit_logs(
        admin,
        module=module,
        action=action,
        actor_id=actor_id,
        result=result,
        skip=(page - 1) * limit,
        limit=limit,
    )
    return [AuditLogPublic.from_log(log) for log in logs]


@router.get("/audit-logs/{log_id}", response_model=AuditLogPublic)
async def get_audit_log(log_id: PydanticObjectId, admin: AdminUser) -> AuditLogPublic:
    return AuditLogPublic.from_log(await service.get_audit_log(admin, log_id))


@router.get("/config", response_model=ConfigPublic)
async def get_config(admin: AdminUser) -> ConfigPublic:
    return ConfigPublic.from_config(await service.get_config())


@router.patch("/config", response_model=ConfigPublic)
async def update_config(data: ConfigUpdate, admin: AdminUser) -> ConfigPublic:
    return ConfigPublic.from_config(await service.update_config(admin, data))
