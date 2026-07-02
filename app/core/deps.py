"""Shared FastAPI dependencies: authentication and role-based authorization.

``get_current_user`` resolves the bearer token to an active user; ``require_roles``
builds a dependency that enforces the caller holds at least one of the given roles.
Ownership checks live in each module's service/route where the resource is known.
"""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from beanie import PydanticObjectId
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

from app.core.errors import AppError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.users.models import Role, User, UserStatus
from app.users.repository import get_by_id

_bearer = HTTPBearer(auto_error=False)


async def _resolve_token_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> User:
    """Resolve a bearer access token to its user, rejecting suspended accounts."""
    if credentials is None:
        raise AppError(
            "Not authenticated", code="not_authenticated", status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        payload = decode_token(credentials.credentials)
    except PyJWTError as exc:
        raise AppError(
            "Invalid or expired token",
            code="invalid_token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise AppError(
            "Invalid token type", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )

    subject = payload.get("sub")
    if not subject:
        raise AppError(
            "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )

    user = await get_by_id(PydanticObjectId(subject))
    if user is None:
        raise AppError(
            "User not found", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )
    if user.status == UserStatus.SUSPENDED:
        raise AppError(
            "Account suspended", code="account_suspended", status_code=status.HTTP_403_FORBIDDEN
        )
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Authenticated, fully-onboarded user. Blocks accounts that still need to
    complete their profile (social sign-up) — those may only use the profile
    endpoints via ``get_current_user_allow_incomplete``."""
    user = await _resolve_token_user(credentials)
    if user.status == UserStatus.PROFILE_INCOMPLETE:
        raise AppError(
            "Complete your profile to continue",
            code="profile_incomplete",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return user


async def get_current_user_allow_incomplete(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Like ``get_current_user`` but allows ``profile_incomplete`` accounts.
    Used by ``GET /me`` and ``POST /me/complete-profile`` so a social user can see
    their status and finish onboarding."""
    return await _resolve_token_user(credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserAllowIncomplete = Annotated[User, Depends(get_current_user_allow_incomplete)]


def require_roles(*roles: Role) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency factory: require the caller to hold at least one of ``roles``."""
    allowed = set(roles)

    async def _checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AppError(
                "Insufficient permissions",
                code="forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return user

    return _checker
