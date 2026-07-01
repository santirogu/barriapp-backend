"""Admin I/O schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.admin.models import PlatformConfig
from app.audit.models import AuditLog, AuditModule, AuditResult, AuditSeverity
from app.users.models import UserStatus


class MetricsResponse(BaseModel):
    users: int
    stores: int
    open_stores: int
    active_collaborators: int
    orders_total: int
    orders_delivered: int
    errands_total: int
    gmv: int  # COP — delivered orders total
    platform_revenue: int  # COP — sum of commission ledger entries


class UserStatusUpdate(BaseModel):
    status: UserStatus


class ConfigUpdate(BaseModel):
    default_commission_rate: float | None = None
    settlement_frequency_days: int | None = None


class ConfigPublic(BaseModel):
    default_commission_rate: float
    settlement_frequency_days: int
    updated_at: datetime

    @classmethod
    def from_config(cls, cfg: PlatformConfig) -> "ConfigPublic":
        return cls(
            default_commission_rate=cfg.default_commission_rate,
            settlement_frequency_days=cfg.settlement_frequency_days,
            updated_at=cfg.updated_at,
        )


class AuditLogPublic(BaseModel):
    id: str
    module: AuditModule
    action: str
    actor_id: str | None
    actor_role: str | None
    target_type: str | None
    target_id: str | None
    result: AuditResult
    severity: AuditSeverity
    changes: dict[str, Any] | None
    meta: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_log(cls, log: AuditLog) -> "AuditLogPublic":
        return cls(
            id=str(log.id),
            module=log.module,
            action=log.action,
            actor_id=str(log.actor_id) if log.actor_id else None,
            actor_role=log.actor_role,
            target_type=log.target_type,
            target_id=str(log.target_id) if log.target_id else None,
            result=log.result,
            severity=log.severity,
            changes=log.changes,
            meta=log.meta,
            created_at=log.created_at,
        )
