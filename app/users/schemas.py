"""Users I/O schemas (Pydantic request/response models)."""

from pydantic import BaseModel, EmailStr

from app.users.models import Role, User, UserStatus


class UserPublic(BaseModel):
    id: str
    phone: str | None
    email: EmailStr | None
    full_name: str
    roles: list[Role]
    status: UserStatus
    avatar_url: str | None

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        return cls(
            id=str(user.id),
            phone=user.phone,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            status=user.status,
            avatar_url=user.avatar_url,
        )


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    avatar_url: str | None = None
