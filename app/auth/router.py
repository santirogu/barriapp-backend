"""Auth endpoints."""

from fastapi import APIRouter, Depends, status

from app.auth import service
from app.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    SocialLoginRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.core.ratelimit import rate_limiter

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest) -> MessageResponse:
    await service.register(data)
    return MessageResponse(message="Registered. Verify the OTP sent to your phone.")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: VerifyOtpRequest) -> TokenResponse:
    return await service.verify_otp(data)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limiter("login"))])
async def login(data: LoginRequest) -> TokenResponse:
    return await service.login(data)


@router.post("/social", response_model=TokenResponse, dependencies=[Depends(rate_limiter("login"))])
async def social_login(data: SocialLoginRequest) -> TokenResponse:
    return await service.social_login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest) -> TokenResponse:
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    # Stateless JWT: the client discards its tokens. Refresh-token revocation
    # (e.g. a Redis denylist) can be added later.
    return None
