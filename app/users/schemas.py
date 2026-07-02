"""Users I/O schemas (Pydantic request/response models)."""

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.logic import MIN_AGE, is_adult
from app.users.models import DocumentType, Gender, Role, User, UserStatus


class UserPublic(BaseModel):
    id: str
    role: Role
    phone: str | None
    email: EmailStr | None
    first_name: str
    last_name: str
    document_type: DocumentType | None
    document_number: str | None
    gender: Gender | None
    birth_date: date | None
    status: UserStatus
    avatar_url: str | None

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        return cls(
            id=str(user.id),
            role=user.role,
            phone=user.phone,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            document_type=user.document_type,
            document_number=user.document_number,
            gender=user.gender,
            birth_date=user.birth_date,
            status=user.status,
            avatar_url=user.avatar_url,
        )


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    avatar_url: str | None = None


class CompleteProfileRequest(BaseModel):
    """Fields a social-login (client) account must provide before activating."""

    document_type: DocumentType
    document_number: str = Field(min_length=3, max_length=40)
    gender: Gender
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def _must_be_adult(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("birth_date cannot be in the future")
        if not is_adult(value, date.today()):
            raise ValueError(f"must be at least {MIN_AGE} years old to register")
        return value
