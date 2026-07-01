"""MongoDB connection and Beanie ODM initialization.

Uses PyMongo's native async client (``AsyncMongoClient``); Motor is deprecated in
favor of it and Beanie 2.x targets it directly.

Domain modules register their Beanie documents by appending to
``DOCUMENT_MODELS`` (typically at import time), and ``init_db`` wires them into
Beanie on application startup. The connection lifecycle is driven by the app
lifespan in ``app.main``.
"""

from typing import Any

from beanie import Document, init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings

MongoClientT = AsyncMongoClient[dict[str, Any]]
MongoDatabaseT = AsyncDatabase[dict[str, Any]]

# Populated by each domain module as its documents are implemented.
DOCUMENT_MODELS: list[type[Document]] = []


class _DatabaseState:
    client: MongoClientT | None = None
    database: MongoDatabaseT | None = None


_state = _DatabaseState()


async def init_db(settings: Settings) -> None:
    """Open the Mongo connection and initialize Beanie with registered models."""
    client: MongoClientT = AsyncMongoClient(settings.mongodb_uri)
    database = client[settings.mongodb_db_name]
    await init_beanie(database=database, document_models=DOCUMENT_MODELS)
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
