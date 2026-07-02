"""Collaborators business logic: onboarding, availability, admin verification."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.collaborators import repository as collab_repo
from app.collaborators.models import (
    Availability,
    CollaboratorDocuments,
    CollaboratorProfile,
    VerificationStatus,
)
from app.collaborators.schemas import AvailabilityUpdate, BecomeCollaborator, VerificationUpdate
from app.core.errors import AppError
from app.users import repository as users_repo
from app.users.models import GeoPoint, Role, User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def resolve_availability(update: AvailabilityUpdate) -> tuple[Availability, GeoPoint | None]:
    """Validate an availability change and return (availability, location). Pure.

    Collaborators may only set ``online`` (requires coordinates) or ``offline``;
    ``on_delivery`` is system-managed.
    """
    if update.status == Availability.ONLINE:
        if update.lng is None or update.lat is None:
            raise AppError(
                "Going online requires lng and lat",
                code="location_required",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Availability.ONLINE, GeoPoint(coordinates=(update.lng, update.lat))
    if update.status == Availability.OFFLINE:
        return Availability.OFFLINE, None
    raise AppError(
        "Collaborators can only go online or offline",
        code="invalid_status",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def become_collaborator(user: User, data: BecomeCollaborator) -> CollaboratorProfile:
    assert user.id is not None  # authenticated, persisted user
    if await collab_repo.get_by_user_id(user.id) is not None:
        raise AppError("Already a collaborator", code="already_collaborator", status_code=409)
    profile = CollaboratorProfile(
        user_id=user.id,
        vehicle_type=data.vehicle_type,
        documents=CollaboratorDocuments(id_number=data.id_number, license_url=data.license_url),
    )
    await collab_repo.insert(profile)
    await audit.record(
        module=AuditModule.DELIVERY,
        action="collaborator.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="collaborator",
        target_id=profile.id,
    )
    return profile


async def list_collaborators(
    *, verification_status: VerificationStatus | None, skip: int, limit: int
) -> list[CollaboratorProfile]:
    """Admin: list collaborator profiles (verification queue), optionally filtered."""
    return await collab_repo.list_by_status(verification_status, skip=skip, limit=limit)


async def get_my_profile(user: User) -> CollaboratorProfile:
    assert user.id is not None  # authenticated, persisted user
    profile = await collab_repo.get_by_user_id(user.id)
    if profile is None:
        raise AppError(
            "Collaborator profile not found",
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return profile


async def set_availability(user: User, data: AvailabilityUpdate) -> CollaboratorProfile:
    profile = await get_my_profile(user)
    if profile.verification_status != VerificationStatus.APPROVED:
        raise AppError(
            "Collaborator is not approved",
            code="not_approved",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    availability, location = resolve_availability(data)
    profile.availability = availability
    profile.current_location = location
    profile.updated_at = _utcnow()
    await profile.save()
    await audit.record(
        module=AuditModule.DELIVERY,
        action="collaborator.availability.changed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="collaborator",
        target_id=profile.id,
        changes={"availability": str(availability)},
    )
    return profile


async def verify(
    admin: User, target_user_id: PydanticObjectId, data: VerificationUpdate
) -> CollaboratorProfile:
    profile = await collab_repo.get_by_user_id(target_user_id)
    if profile is None:
        raise AppError(
            "Collaborator profile not found",
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    previous = profile.verification_status
    profile.verification_status = data.status
    profile.updated_at = _utcnow()
    await profile.save()

    # On approval, grant the collaborator role.
    if data.status == VerificationStatus.APPROVED:
        target = await users_repo.get_by_id(target_user_id)
        if target is not None and Role.COLLABORATOR not in target.roles:
            target.roles.append(Role.COLLABORATOR)
            target.updated_at = _utcnow()
            await target.save()
            await audit.record(
                module=AuditModule.USERS,
                action="user.role.granted",
                actor_id=admin.id,
                actor_role=primary_role(admin),
                target_type="user",
                target_id=target_user_id,
                changes={"role": "collaborator"},
            )

    await audit.record(
        module=AuditModule.DELIVERY,
        action="collaborator.verification.changed",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="collaborator",
        target_id=profile.id,
        changes={"before": str(previous), "after": str(data.status), "reason": data.reason},
    )
    return profile
