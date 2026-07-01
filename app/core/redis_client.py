"""Redis connection lifecycle (cache, pub/sub, and queue broker).

Used later for caching, live-tracking pub/sub, and background job brokering.
The connection lifecycle is driven by the app lifespan in ``app.main``.
"""

from redis.asyncio import Redis

from app.core.config import Settings


class _RedisState:
    client: "Redis | None" = None


_state = _RedisState()


async def init_redis(settings: Settings) -> None:
    """Open the Redis connection."""
    _state.client = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Close the Redis connection (idempotent)."""
    if _state.client is not None:
        await _state.client.aclose()
        _state.client = None


async def ping_redis() -> bool:
    """Return True if Redis responds to a ping (used by readiness checks)."""
    if _state.client is None:
        return False
    try:
        return bool(await _state.client.ping())
    except Exception:
        return False


def get_redis() -> Redis:
    """Return the active Redis client (raises if not initialized)."""
    if _state.client is None:
        raise RuntimeError("Redis is not initialized")
    return _state.client
