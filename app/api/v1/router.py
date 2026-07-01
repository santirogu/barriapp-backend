"""Aggregates all v1 routers.

As domain modules are implemented, include their routers here.
"""

from fastapi import APIRouter

from app.admin.router import router as admin_router
from app.api.v1 import health
from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.collaborators.router import router as collaborators_router
from app.delivery.router import router as delivery_router
from app.delivery.ws import router as delivery_ws_router
from app.errands.router import router as errands_router
from app.notifications.router import router as notifications_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.reviews.router import router as reviews_router
from app.stores.router import router as stores_router
from app.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(users_router)
api_router.include_router(stores_router)
api_router.include_router(catalog_router)
api_router.include_router(orders_router)
api_router.include_router(collaborators_router)
api_router.include_router(delivery_router)
api_router.include_router(delivery_ws_router)
api_router.include_router(payments_router)
api_router.include_router(errands_router)
api_router.include_router(reviews_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
