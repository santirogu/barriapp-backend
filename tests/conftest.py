"""Shared pytest fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

# Settings load lazily (get_settings is called inside create_app), so setting this
# at import time — before any app instance is built — keeps tests off a local .env.
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture
async def client() -> AsyncClient:
    """An HTTP client bound to a fresh app instance (in-process, no network)."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
