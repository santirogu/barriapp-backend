"""Auth business logic: registration, OTP verification, login, token refresh.

Every security-relevant event (including failures) is recorded in the audit trail
(see docs/AUDIT_LOG.md).
"""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status
from jwt import PyJWTError

from app.audit import service as audit
from app.audit.models import AuditModule, AuditResult, AuditSeverity
from app.auth import otp, sms, social
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    SocialLoginRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.auth.social import SocialIdentity, SocialProvider
from app.core.errors import AppError
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.users import repository as users_repo
from app.users.models import Consent, User, UserStatus
from app.users.service import primary_role

CONSENT_VERSION = "1.0"


def _tokens(user: User) -> TokenResponse:
    roles = [str(role) for role in user.roles]
    return TokenResponse(
        access_token=create_access_token(str(user.id), roles),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def register(data: RegisterRequest) -> None:
    if not data.accept_habeas_data:
        raise AppError(
            "Habeas Data consent is required",
            code="consent_required",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if await users_repo.get_by_phone(data.phone) is not None:
        raise AppError(
            "Phone already registered", code="phone_taken", status_code=status.HTTP_409_CONFLICT
        )
    if data.email is not None and await users_repo.get_by_email(data.email) is not None:
        raise AppError(
            "Email already registered", code="email_taken", status_code=status.HTTP_409_CONFLICT
        )

    user = User(
        phone=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        consent=Consent(habeas_data=True, version=CONSENT_VERSION, accepted_at=datetime.now(UTC)),
    )
    await users_repo.insert(user)

    code = await otp.issue_otp(data.phone)
    await sms.send_otp(data.phone, code)

    await audit.record(
        module=AuditModule.AUTH,
        action="auth.register",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
    )


async def verify_otp(data: VerifyOtpRequest) -> TokenResponse:
    user = await users_repo.get_by_phone(data.phone)
    if user is None:
        raise AppError("User not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)

    if not await otp.verify_otp(data.phone, data.code):
        await audit.record(
            module=AuditModule.AUTH,
            action="auth.otp.failed",
            result=AuditResult.FAILURE,
            severity=AuditSeverity.WARNING,
            target_type="user",
            target_id=user.id,
        )
        raise AppError(
            "Invalid or expired code", code="invalid_otp", status_code=status.HTTP_400_BAD_REQUEST
        )

    if user.status == UserStatus.PENDING_VERIFICATION:
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.now(UTC)
        await user.save()

    await audit.record(
        module=AuditModule.AUTH,
        action="auth.otp.verified",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
    )
    return _tokens(user)


async def login(data: LoginRequest) -> TokenResponse:
    user = await users_repo.get_by_phone(data.phone)
    if (
        user is None
        or user.password_hash is None
        or not verify_password(data.password, user.password_hash)
    ):
        await audit.record(
            module=AuditModule.AUTH,
            action="auth.login.failed",
            result=AuditResult.FAILURE,
            severity=AuditSeverity.WARNING,
            target_type="user",
            target_id=user.id if user is not None else None,
            changes={"phone": data.phone},
        )
        raise AppError(
            "Invalid credentials",
            code="invalid_credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if user.status == UserStatus.SUSPENDED:
        raise AppError(
            "Account suspended", code="account_suspended", status_code=status.HTTP_403_FORBIDDEN
        )
    if user.status == UserStatus.PENDING_VERIFICATION:
        raise AppError(
            "Account not verified", code="not_verified", status_code=status.HTTP_403_FORBIDDEN
        )

    await audit.record(
        module=AuditModule.AUTH,
        action="auth.login.success",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
    )
    return _tokens(user)


async def refresh(refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except PyJWTError as exc:
        raise AppError(
            "Invalid or expired token",
            code="invalid_token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise AppError(
            "Invalid token type", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )

    subject = payload.get("sub")
    user = await users_repo.get_by_id(PydanticObjectId(subject)) if subject else None
    if user is None:
        raise AppError(
            "User not found", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )
    if user.status == UserStatus.SUSPENDED:
        raise AppError(
            "Account suspended", code="account_suspended", status_code=status.HTTP_403_FORBIDDEN
        )

    await audit.record(
        module=AuditModule.AUTH,
        action="auth.token.refresh",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
    )
    return _tokens(user)


def _apply_provider(user: User, identity: SocialIdentity) -> None:
    if identity.provider == SocialProvider.GOOGLE:
        user.google_sub = identity.subject
    else:
        user.apple_sub = identity.subject


async def _find_by_provider(identity: SocialIdentity) -> User | None:
    if identity.provider == SocialProvider.GOOGLE:
        return await users_repo.get_by_google_sub(identity.subject)
    return await users_repo.get_by_apple_sub(identity.subject)


async def social_login(data: SocialLoginRequest) -> TokenResponse:
    """Verify a Google/Apple ID token and log in (creating/linking the account)."""
    identity = await social.verify_token(data.provider, data.id_token)

    user = await _find_by_provider(identity)
    linked = False
    if user is None and identity.email is not None:
        # Link the provider to an existing account with the same email.
        user = await users_repo.get_by_email(identity.email)
        if user is not None:
            _apply_provider(user, identity)
            user.updated_at = datetime.now(UTC)
            await user.save()
            linked = True

    if user is None:
        user = User(
            full_name=identity.full_name or "Usuario BarriApp",
            email=identity.email,
            status=UserStatus.ACTIVE,  # email verified by the provider
            consent=Consent(
                habeas_data=True, version=CONSENT_VERSION, accepted_at=datetime.now(UTC)
            ),
        )
        _apply_provider(user, identity)
        await users_repo.insert(user)
        await audit.record(
            module=AuditModule.AUTH,
            action="auth.social.register",
            actor_id=user.id,
            actor_role=primary_role(user),
            target_type="user",
            target_id=user.id,
            changes={"provider": data.provider.value},
        )

    if user.status == UserStatus.SUSPENDED:
        raise AppError(
            "Account suspended", code="account_suspended", status_code=status.HTTP_403_FORBIDDEN
        )

    await audit.record(
        module=AuditModule.AUTH,
        action="auth.social.login",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="user",
        target_id=user.id,
        changes={"provider": data.provider.value, "linked_existing": linked},
    )
    return _tokens(user)
