"""Audit log model (Beanie) — append-only trail, super_admin-readable.

See docs/AUDIT_LOG.md. Entries are never updated or deleted by the application.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class AuditModule(StrEnum):
    AUTH = "auth"
    USERS = "users"
    STORES = "stores"
    CATALOG = "catalog"
    ORDERS = "orders"
    ERRANDS = "errands"
    DELIVERY = "delivery"
    PAYMENTS = "payments"
    REVIEWS = "reviews"
    NOTIFICATIONS = "notifications"
    AI = "ai"
    ADMIN = "admin"


class AuditResult(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AuditLog(Document):
    module: AuditModule
    action: str  # canonical code: module.entity.verb, e.g. "auth.login.success"
    actor_id: PydanticObjectId | None = None
    actor_role: str | None = None
    target_type: str | None = None
    target_id: PydanticObjectId | None = None
    changes: dict[str, Any] | None = None
    result: AuditResult = AuditResult.SUCCESS
    severity: AuditSeverity = AuditSeverity.INFO
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "audit_logs"
        indexes = [  # noqa: RUF012
            IndexModel([("created_at", -1)]),
            IndexModel([("module", 1), ("action", 1), ("created_at", -1)]),
            IndexModel([("actor_id", 1), ("created_at", -1)]),
            IndexModel([("target_type", 1), ("target_id", 1), ("created_at", -1)]),
            IndexModel([("result", 1), ("severity", 1), ("created_at", -1)]),
        ]
