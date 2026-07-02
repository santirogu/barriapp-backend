"""Collaborator endpoints. See docs/API_CONTRACT.md §2/§9 and
docs/COLLABORATOR_ONBOARDING.md."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, status

from app.collaborators import service
from app.collaborators.models import VerificationStatus
from app.collaborators.schemas import (
    AvailabilityUpdate,
    BecomeCollaborator,
    CollaboratorProfilePublic,
    VerificationUpdate,
)
from app.core.deps import CurrentUser, require_roles
from app.users.models import Role, User

router = APIRouter(tags=["collaborators"])

AdminUser = Annotated[User, Depends(require_roles(Role.SUPER_ADMIN))]


@router.get("/admin/collaborators", response_model=list[CollaboratorProfilePublic])
async def list_collaborators(
    admin: AdminUser,
    verification_status: VerificationStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> list[CollaboratorProfilePublic]:
    profiles = await service.list_collaborators(
        verification_status=verification_status, skip=(page - 1) * limit, limit=limit
    )
    return [CollaboratorProfilePublic.from_profile(p) for p in profiles]


@router.post(
    "/me/become-collaborator",
    response_model=CollaboratorProfilePublic,
    status_code=status.HTTP_201_CREATED,
)
async def become_collaborator(
    data: BecomeCollaborator, user: CurrentUser
) -> CollaboratorProfilePublic:
    return CollaboratorProfilePublic.from_profile(await service.become_collaborator(user, data))


@router.get("/collaborator/me", response_model=CollaboratorProfilePublic)
async def get_my_profile(user: CurrentUser) -> CollaboratorProfilePublic:
    return CollaboratorProfilePublic.from_profile(await service.get_my_profile(user))


@router.post("/collaborator/availability", response_model=CollaboratorProfilePublic)
async def set_availability(
    data: AvailabilityUpdate, user: CurrentUser
) -> CollaboratorProfilePublic:
    return CollaboratorProfilePublic.from_profile(await service.set_availability(user, data))


@router.patch("/collaborator/{user_id}/verification", response_model=CollaboratorProfilePublic)
async def verify_collaborator(
    user_id: PydanticObjectId, data: VerificationUpdate, admin: AdminUser
) -> CollaboratorProfilePublic:
    return CollaboratorProfilePublic.from_profile(await service.verify(admin, user_id, data))
