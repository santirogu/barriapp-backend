"""Redis fixed-window rate limiting, applied as a FastAPI dependency.

Protects abuse-prone endpoints (login brute-force, AI chat cost) per client IP.
Best-effort: if Redis is unavailable the request is allowed (fail-open) rather
than breaking the API.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

import structlog
from fastapi import Request, status

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.redis_client import get_redis

logger = structlog.get_logger()

RateScope = Literal["login", "ai_chat"]


def _limits(settings: Settings) -> dict[str, tuple[int, int]]:
    return {
        "login": (settings.login_rate_limit, settings.login_rate_window),
        "ai_chat": (settings.ai_chat_rate_limit, settings.ai_chat_rate_window),
    }


async def _hit(key: str, limit: int, window: int) -> None:
    """Increment the window counter; raise 429 when the limit is exceeded."""
    try:
        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
    except AppError:
        raise
    except Exception:
        logger.exception("rate_limit_check_failed_allowing", key=key)
        return
    if count > limit:
        raise AppError(
            "Too many requests, please slow down.",
            code="rate_limited",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


def rate_limiter(scope: RateScope) -> Callable[[Request], Awaitable[None]]:
    """Build a dependency that rate-limits ``scope`` by client IP."""

    async def _dependency(request: Request) -> None:
        settings = get_settings()
        limit, window = _limits(settings)[scope]
        identifier = request.client.host if request.client else "unknown"
        await _hit(f"rl:{scope}:{identifier}", limit, window)

    return _dependency
