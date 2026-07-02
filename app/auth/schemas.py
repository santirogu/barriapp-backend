"""Auth I/O schemas."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.logic import MIN_AGE, is_adult
from app.auth.social import SocialProvider
from app.users.models import DocumentType, Gender, Role


class _RegisterBase(BaseModel):
    """Fields required for every role at registration."""

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    document_type: DocumentType
    document_number: str = Field(min_length=3, max_length=40)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accept_habeas_data: bool


class _WithBirthAndGender(_RegisterBase):
    """Shared by roles that must be adults (client, collaborator)."""

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


class SellerRegister(_RegisterBase):
    role: Literal[Role.SELLER]


class ClientRegister(_WithBirthAndGender):
    role: Literal[Role.CLIENT]


class CollaboratorRegister(_WithBirthAndGender):
    role: Literal[Role.COLLABORATOR]


# Discriminated by `role`: FastAPI validates the correct shape per role.
RegisterRequest = Annotated[
    SellerRegister | ClientRegister | CollaboratorRegister,
    Field(discriminator="role"),
]


class MessageResponse(BaseModel):
    message: str


class VerifyOtpRequest(BaseModel):
    phone: str
    code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    phone: str
    password: str


class SocialLoginRequest(BaseModel):
    provider: SocialProvider
    id_token: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
