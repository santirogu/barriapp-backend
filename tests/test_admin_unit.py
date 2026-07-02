"""Unit tests for the RBAC guard used across admin endpoints (no DB)."""

from types import SimpleNamespace

import pytest

from app.core.deps import require_roles
from app.core.errors import AppError
from app.users.models import Role


@pytest.mark.req("AD-2")
async def test_require_roles_allows_holder() -> None:
    checker = require_roles(Role.SUPER_ADMIN)
    admin = SimpleNamespace(id="1", role=Role.SUPER_ADMIN)
    assert await checker(admin) is admin  # type: ignore[arg-type]


@pytest.mark.req("AD-2")
async def test_require_roles_rejects_others() -> None:
    checker = require_roles(Role.SUPER_ADMIN)
    client = SimpleNamespace(id="1", role=Role.CLIENT)
    with pytest.raises(AppError) as exc:
        await checker(client)  # type: ignore[arg-type]
    assert exc.value.status_code == 403
    assert exc.value.code == "forbidden"
