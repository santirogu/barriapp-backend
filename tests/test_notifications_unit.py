"""Unit tests for notification logic (no DB): token dedup + mark-read authz."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.notifications import service as notifications_service
from app.notifications.service import with_token


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("U-3")
def test_with_token_dedup() -> None:
    assert with_token([], "a") == ["a"]
    assert with_token(["a"], "b") == ["a", "b"]
    assert with_token(["a"], "a") == ["a"]  # no duplicate


@pytest.mark.req("N-2")
async def test_mark_read_only_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[])
    other_notification = SimpleNamespace(user_id=PydanticObjectId(), read=False)
    monkeypatch.setattr(notifications_service.notif_repo, "get_by_id", _returns(other_notification))

    with pytest.raises(AppError) as exc:
        await notifications_service.mark_read(user, PydanticObjectId())
    assert exc.value.status_code == 403
