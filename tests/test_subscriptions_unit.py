"""Unit tests for subscription authorization (no DB)."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.subscriptions import service as sub_service
from app.users.models import Role


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("SUB-2")
async def test_subscribe_by_non_owner_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    store = SimpleNamespace(owner_id=PydanticObjectId())  # owned by someone else
    user = SimpleNamespace(id=PydanticObjectId(), roles=[Role.SELLER])
    monkeypatch.setattr(sub_service.stores_repo, "get_by_id", _returns(store))

    with pytest.raises(AppError) as exc:
        await sub_service.subscribe(user, PydanticObjectId())
    assert exc.value.status_code == 403
