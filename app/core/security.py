"""Password hashing and JWT creation/verification.

Access tokens carry the subject (user id) and roles; refresh tokens carry only
the subject. Both are signed with the configured secret/algorithm.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

# Argon2 (maintained, modern); no bcrypt 72-byte limitation.
_password_hasher = PasswordHash.recommended()

# Token *type* labels (not secrets). nosec: B105 false positive.
ACCESS_TOKEN_TYPE = "access"  # nosec B105
REFRESH_TOKEN_TYPE = "refresh"  # nosec B105


def hash_password(password: str) -> str:
    return str(_password_hasher.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return bool(_password_hasher.verify(password, password_hash))


def _create_token(
    subject: str, token_type: str, expires_delta: timedelta, extra: dict[str, Any] | None = None
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra:
        payload.update(extra)
    token: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_access_token(subject: str, roles: list[str]) -> str:
    settings = get_settings()
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
        extra={"roles": roles},
    )


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises ``jwt.PyJWTError`` on invalid/expired tokens."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    return payload
