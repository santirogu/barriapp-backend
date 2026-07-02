"""Users business logic."""

from datetime import UTC, datetime
from typing import Any

from app.audit import service as audit
from app.audit.models import AuditModule
from app.users.models import User
from app.users.schemas import UserUpdate


def primary_role(user: User) -> str:
    return str(user.role)


async def update_profile(user: User, data: UserUpdate) -> User:
    """Apply a partial profile update, recording a before/after audit diff."""
    changes: dict[str, Any] = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        current = getattr(user, field)
        if current != value:
            changes[field] = {"before": current, "after": value}
            setattr(user, field, value)

    if changes:
        user.updated_at = datetime.now(UTC)
        await user.save()
        await audit.record(
            module=AuditModule.USERS,
            action="user.updated",
            actor_id=user.id,
            actor_role=primary_role(user),
            target_type="user",
            target_id=user.id,
            changes=changes,
        )
    return user
