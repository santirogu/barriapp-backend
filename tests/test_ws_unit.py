"""Unit tests for WebSocket token resolution (no DB/socket)."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from jose import JWTError

from app.delivery import ws as ws_mod
from app.users.models import UserStatus


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("D-4")
async def test_resolve_ws_user_missing_token() -> None:
    assert await ws_mod.resolve_ws_user(None) is None
    assert await ws_mod.resolve_ws_user("") is None


@pytest.mark.req("D-4")
async def test_resolve_ws_user_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_t: str) -> dict[str, object]:
        raise JWTError("bad")

    monkeypatch.setattr(ws_mod, "decode_token", _raise)
    assert await ws_mod.resolve_ws_user("bad") is None


@pytest.mark.req("D-4")
async def test_resolve_ws_user_wrong_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ws_mod, "decode_token", lambda _t: {"type": "refresh", "sub": "x"})
    assert await ws_mod.resolve_ws_user("t") is None


@pytest.mark.req("D-4")
async def test_resolve_ws_user_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    oid = PydanticObjectId()
    user = SimpleNamespace(id=oid, status=UserStatus.ACTIVE)
    monkeypatch.setattr(ws_mod, "decode_token", lambda _t: {"type": "access", "sub": str(oid)})
    monkeypatch.setattr(ws_mod.users_repo, "get_by_id", _returns(user))
    assert await ws_mod.resolve_ws_user("t") is user


@pytest.mark.req("D-4")
async def test_resolve_ws_user_suspended(monkeypatch: pytest.MonkeyPatch) -> None:
    oid = PydanticObjectId()
    user = SimpleNamespace(id=oid, status=UserStatus.SUSPENDED)
    monkeypatch.setattr(ws_mod, "decode_token", lambda _t: {"type": "access", "sub": str(oid)})
    monkeypatch.setattr(ws_mod.users_repo, "get_by_id", _returns(user))
    assert await ws_mod.resolve_ws_user("t") is None
