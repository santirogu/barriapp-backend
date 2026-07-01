"""Social login: verify a provider ID token and extract the identity.

The client (web/mobile) runs the Google/Apple sign-in flow and sends us the
resulting **ID token**; we verify it here and map it to a BarriApp user.

Real verification is networked (provider JWKS) and provider-SDK-specific, so it's
isolated in ``verify_token`` and only enabled when the provider's client id is
configured. Tests monkeypatch ``verify_token`` to stay hermetic.
"""

from dataclasses import dataclass
from enum import StrEnum

import anyio
from fastapi import status

from app.core.config import get_settings
from app.core.errors import AppError


class SocialProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"


@dataclass
class SocialIdentity:
    provider: SocialProvider
    subject: str  # provider-stable user id (the token's `sub`)
    email: str | None
    full_name: str | None


def _not_configured(provider: SocialProvider) -> AppError:
    return AppError(
        f"{provider.value} login is not configured",
        code="provider_not_configured",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
    )


def _invalid_token() -> AppError:
    return AppError(
        "Invalid social token",
        code="invalid_social_token",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


async def _verify_google(id_token: str, client_id: str) -> SocialIdentity:
    def _run() -> dict[str, object]:
        # Lazy import: `pip install google-auth` to enable Google login.
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token

        claims: dict[str, object] = dict(
            g_id_token.verify_oauth2_token(id_token, g_requests.Request(), client_id)
        )
        return claims

    try:
        info = await anyio.to_thread.run_sync(_run)
    except Exception as exc:  # invalid signature/aud/exp, network, etc.
        raise _invalid_token() from exc
    return SocialIdentity(
        provider=SocialProvider.GOOGLE,
        subject=str(info["sub"]),
        email=info.get("email"),  # type: ignore[arg-type]
        full_name=info.get("name"),  # type: ignore[arg-type]
    )


async def _verify_apple(id_token: str, client_id: str) -> SocialIdentity:
    def _run() -> dict[str, object]:
        # Lazy imports; verify against Apple's JWKS (iss https://appleid.apple.com).
        import json
        from urllib.request import urlopen

        from jose import jwt

        with urlopen("https://appleid.apple.com/auth/keys", timeout=5) as resp:  # nosec B310
            jwks = json.loads(resp.read())
        headers = jwt.get_unverified_header(id_token)
        key = next(k for k in jwks["keys"] if k["kid"] == headers["kid"])
        claims: dict[str, object] = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://appleid.apple.com",
        )
        return claims

    try:
        claims = await anyio.to_thread.run_sync(_run)
    except Exception as exc:
        raise _invalid_token() from exc
    return SocialIdentity(
        provider=SocialProvider.APPLE,
        subject=str(claims["sub"]),
        email=claims.get("email"),  # type: ignore[arg-type]
        full_name=None,  # Apple only returns the name on first consent (sent separately)
    )


async def verify_token(provider: SocialProvider, id_token: str) -> SocialIdentity:
    settings = get_settings()
    if provider == SocialProvider.GOOGLE:
        if not settings.google_client_id:
            raise _not_configured(provider)
        return await _verify_google(id_token, settings.google_client_id)
    if not settings.apple_client_id:
        raise _not_configured(provider)
    return await _verify_apple(id_token, settings.apple_client_id)
