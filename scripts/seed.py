"""Database seed script.

Connects to MongoDB and initializes Beanie, then seeds reference data. It is
idempotent by design: re-running should not create duplicates.

Run with:
    uv run python -m scripts.seed

Currently a scaffold — as domain models are implemented, add seeding for:
- store/product categories (reference data)
- the initial super_admin user
"""

import asyncio

from app.core.config import get_settings
from app.core.db import close_db, init_db


async def seed() -> None:
    settings = get_settings()
    await init_db(settings)
    try:
        # TODO: seed categories and the initial super_admin once models exist.
        print(f"Connected to MongoDB db='{settings.mongodb_db_name}'. Nothing to seed yet.")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
