"""Integration test fixtures backed by real MongoDB and Redis (testcontainers).

A session-scoped pair of containers is started once; each test gets an in-process
HTTP client wired to the initialized DB/Redis. Requires a running Docker daemon.
"""

import os
import shutil
import subprocess
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from testcontainers.mongodb import MongoDbContainer
from testcontainers.redis import RedisContainer

from app.core.config import get_settings
from app.core.db import close_db, init_db
from app.core.redis_client import close_redis, get_redis, init_redis
from app.main import create_app

RegisterUser = Callable[[str], Awaitable[dict[str, str]]]


def _ensure_docker_host() -> None:
    """Point testcontainers (docker-py) at the active Docker socket.

    docker-py doesn't read Docker CLI contexts, so on setups whose socket isn't
    at ``/var/run/docker.sock`` (e.g. Rancher Desktop / Colima) we resolve it from
    the CLI. On standard CI (default socket present) this is a no-op.
    """
    if os.environ.get("DOCKER_HOST") or os.path.exists("/var/run/docker.sock"):
        return
    docker = shutil.which("docker")
    if docker is None:
        return
    try:
        host = subprocess.check_output(
            [docker, "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            text=True,
        ).strip()
    except (subprocess.SubprocessError, OSError):
        return
    if host:
        os.environ["DOCKER_HOST"] = host
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


_ensure_docker_host()


@pytest.fixture(scope="session")
def _services() -> Iterator[None]:
    with (
        MongoDbContainer("mongo:7") as mongo,
        RedisContainer("redis:7-alpine") as redis,
    ):
        os.environ["ENVIRONMENT"] = "test"
        os.environ["MONGODB_URI"] = mongo.get_connection_url()
        os.environ["MONGODB_DB_NAME"] = "barriapp_test"
        os.environ["REDIS_URL"] = (
            f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
        )
        get_settings.cache_clear()
        yield


@pytest_asyncio.fixture
async def api(_services: None) -> AsyncIterator[AsyncClient]:
    settings = get_settings()
    await init_db(settings)
    await init_redis(settings)
    app = create_app()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await close_redis()
        await close_db()


@pytest_asyncio.fixture
async def register_user(api: AsyncClient) -> RegisterUser:
    """Return a helper that registers + OTP-verifies a user and yields their tokens."""

    async def _register(phone: str) -> dict[str, str]:
        resp = await api.post(
            "/api/v1/auth/register",
            json={
                "phone": phone,
                "password": "supersecret",
                "full_name": "Test User",
                "accept_habeas_data": True,
            },
        )
        assert resp.status_code == 201, resp.text
        code = await get_redis().get(f"otp:{phone}")
        resp = await api.post("/api/v1/auth/verify-otp", json={"phone": phone, "code": code})
        assert resp.status_code == 200, resp.text
        tokens: dict[str, str] = resp.json()
        return tokens

    return _register
