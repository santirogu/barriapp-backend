"""Central audit-recording service used by every module.

Call ``record(...)`` at the point of a state change or security event. Request
context (request_id, ip, user_agent) is pulled automatically from the structlog
contextvars bound by ``RequestContextMiddleware`` — callers don't pass it.

The write is append-only (insert only); no update/delete is exposed. For the MVP
the write is synchronous; it can move behind the async queue later (see
docs/AUDIT_LOG.md) without changing this call site.
"""

from typing import Any

import structlog
from beanie import PydanticObjectId

from app.audit.models import AuditLog, AuditModule, AuditResult, AuditSeverity

logger = structlog.get_logger()


async def record(
    *,
    module: AuditModule,
    action: str,
    actor_id: PydanticObjectId | None = None,
    actor_role: str | None = None,
    target_type: str | None = None,
    target_id: PydanticObjectId | None = None,
    changes: dict[str, Any] | None = None,
    result: AuditResult = AuditResult.SUCCESS,
    severity: AuditSeverity = AuditSeverity.INFO,
) -> None:
    ctx = structlog.contextvars.get_contextvars()
    meta = {
        "request_id": ctx.get("request_id"),
        "ip": ctx.get("client_ip"),
        "user_agent": ctx.get("user_agent"),
    }
    entry = AuditLog(
        module=module,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        target_type=target_type,
        target_id=target_id,
        changes=changes,
        result=result,
        severity=severity,
        meta=meta,
    )
    try:
        await entry.insert()
    except Exception:
        # Auditing must never break the main request; log and move on.
        logger.exception("audit_write_failed", action=action, module=str(module))
