"""Users business logic."""

from datetime import UTC, datetime
from typing import Any

from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.errors import AppError
from app.users.models import User, UserStatus
from app.users.schemas import CompleteProfileRequest, UserUpdate


def primary_role(user: User) -> str:
    return str(user.role)


async def complete_profile(user: User, data: CompleteProfileRequest) -> User:
    """Fill the per-role fields missing after social sign-up and activate."""
    if user.status != UserStatus.PROFILE_INCOMPLETE:
        raise AppError(
            "Profile is already complete",
            code="profile_already_complete",
            status_code=status.HTTP_409_CONFLICT,
        )
    user.document_type = data.document_type
    user.document_number = data.document_number
    user.gender = data.gender
    user.birth_date = data.birth_date
    user.status = UserStatus.ACTIVE
    user.updated_at = datetime.now(UTC)
    await user.save()
    await audit.record(
        module=AuditModule.USERS,
        action="user.profile.completed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
    )
    return user


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
