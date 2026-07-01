"""Health and readiness endpoints.

- ``/health``  — liveness: the process is up (no dependency checks).
- ``/health/ready`` — readiness: MongoDB and Redis are reachable. Returns 503 if
  any dependency is down (useful for orchestrators / load balancers).
"""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import ping_db
from app.core.redis_client import ping_redis

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    environment: str
    app: str


class ReadinessResponse(BaseModel):
    ready: bool
    mongodb: bool
    redis: bool


@router.get("/health", summary="Liveness check")
async def health() -> HealthResponse:
    """Return basic service status (process is up)."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        app=settings.app_name,
    )


@router.get("/health/ready", summary="Readiness check (dependencies)")
async def readiness(response: Response) -> ReadinessResponse:
    """Check that MongoDB and Redis are reachable; 503 if any is down."""
    mongodb_ok = await ping_db()
    redis_ok = await ping_redis()
    ready = mongodb_ok and redis_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(ready=ready, mongodb=mongodb_ok, redis=redis_ok)
