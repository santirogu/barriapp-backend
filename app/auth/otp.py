"""One-time-password (OTP) issuance and verification, backed by Redis with TTL."""

import secrets

from app.core.redis_client import get_redis

OTP_TTL_SECONDS = 300
_OTP_KEY = "otp:{phone}"


async def issue_otp(phone: str) -> str:
    """Generate a 6-digit code, store it with a TTL, and return it."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    await get_redis().set(_OTP_KEY.format(phone=phone), code, ex=OTP_TTL_SECONDS)
    return code


async def verify_otp(phone: str, code: str) -> bool:
    """Return True and consume the code if it matches the stored one."""
    redis = get_redis()
    key = _OTP_KEY.format(phone=phone)
    stored = await redis.get(key)
    if stored is not None and stored == code:
        await redis.delete(key)
        return True
    return False
