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
from jose import JWTError

from app.core.errors import AppError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.users.models import Role, User, UserStatus
from app.users.repository import get_by_id

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AppError(
            "Not authenticated", code="not_authenticated", status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
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


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency factory: require the caller to hold at least one of ``roles``."""
    allowed = set(roles)

    async def _checker(user: CurrentUser) -> User:
        if not allowed.intersection(user.roles):
            raise AppError(
                "Insufficient permissions",
                code="forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return user

    return _checker
