"""MongoDB connection and Beanie ODM initialization.

Uses PyMongo's native async client (``AsyncMongoClient``); Motor is deprecated in
favor of it and Beanie 2.x targets it directly.

Domain modules register their Beanie documents in ``_document_models``, and
``init_db`` wires them into Beanie on application startup. The connection
lifecycle is driven by the app lifespan in ``app.main``.
"""

from typing import Any

from beanie import Document, init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings

MongoClientT = AsyncMongoClient[dict[str, Any]]
MongoDatabaseT = AsyncDatabase[dict[str, Any]]


def _document_models() -> list[type[Document]]:
    """Collect all Beanie document models to register with Beanie.

    Imported lazily (inside the function) to avoid import cycles and to keep the
    registry in one place as new modules add documents.
    """
    from app.audit.models import AuditLog
    from app.catalog.models import Category, Product
    from app.collaborators.models import CollaboratorProfile
    from app.orders.models import Order
    from app.stores.models import Store
    from app.users.models import User

    return [AuditLog, User, Store, Category, Product, Order, CollaboratorProfile]


class _DatabaseState:
    client: MongoClientT | None = None
    database: MongoDatabaseT | None = None


_state = _DatabaseState()


async def init_db(settings: Settings) -> None:
    """Open the Mongo connection and initialize Beanie with registered models."""
    client: MongoClientT = AsyncMongoClient(settings.mongodb_uri)
    database = client[settings.mongodb_db_name]
    await init_beanie(database=database, document_models=_document_models())
    _state.client = client
    _state.database = database


async def close_db() -> None:
    """Close the Mongo connection (idempotent)."""
    if _state.client is not None:
        await _state.client.close()
        _state.client = None
        _state.database = None


def get_database() -> MongoDatabaseT:
    """Return the active database handle (raises if not initialized)."""
    if _state.database is None:
        raise RuntimeError("Database is not initialized")
    return _state.database


async def ping_db() -> bool:
    """Return True if MongoDB responds to a ping (used by readiness checks)."""
    if _state.client is None:
        return False
    try:
        await _state.client.admin.command("ping")
    except Exception:
        return False
    return True
