"""Users endpoints (current-user profile)."""

from fastapi import APIRouter

from app.core.deps import CurrentUser, CurrentUserAllowIncomplete
from app.users import service
from app.users.schemas import CompleteProfileRequest, UserPublic, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserPublic, summary="Get my profile")
async def get_me(user: CurrentUserAllowIncomplete) -> UserPublic:
    return UserPublic.from_user(user)


@router.patch("/me", response_model=UserPublic, summary="Update my profile")
async def update_me(data: UserUpdate, user: CurrentUser) -> UserPublic:
    updated = await service.update_profile(user, data)
    return UserPublic.from_user(updated)


@router.post(
    "/me/complete-profile",
    response_model=UserPublic,
    summary="Complete a social-signup profile and activate the account",
)
async def complete_profile(
    data: CompleteProfileRequest, user: CurrentUserAllowIncomplete
) -> UserPublic:
    updated = await service.complete_profile(user, data)
    return UserPublic.from_user(updated)
