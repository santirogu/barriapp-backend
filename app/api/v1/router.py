"""Aggregates all v1 routers.

As domain modules are implemented, include their routers here, e.g.:
    from app.auth.router import router as auth_router
    api_router.include_router(auth_router, prefix="/auth")
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
