"""Unit tests for stores/catalog authorization and decision logic (no DB).

Beanie documents can't be instantiated without ``init_beanie``, so these tests
use lightweight duck-typed stand-ins for the ``user``/``store`` the service reads,
and mock the repository. They exercise the authorization branches that raise
*before* any DB write.
"""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.catalog import service as catalog_service
from app.catalog.schemas import ProductCreate
from app.catalog.service import audit_action_for
from app.core.errors import AppError
from app.stores import service as stores_service
from app.stores.models import StoreStatus
from app.stores.schemas import StoreStatusUpdate, StoreUpdate
from app.users.models import Role


def _returns(value: object):
    async def _inner(*_args: object, **_kwargs: object) -> object:
        return value

    return _inner


def _user(*roles: Role) -> SimpleNamespace:
    return SimpleNamespace(id=PydanticObjectId(), role=roles[0] if roles else Role.CLIENT)


def _store(owner_id: PydanticObjectId, status: StoreStatus = StoreStatus.CLOSED) -> SimpleNamespace:
    return SimpleNamespace(id=PydanticObjectId(), owner_id=owner_id, status=status)


# --- pure decision logic ---


@pytest.mark.req("S-3")
def test_audit_action_for_availability_toggle() -> None:
    assert audit_action_for({"is_available"}) == "product.availability.changed"


@pytest.mark.req("S-3")
def test_audit_action_for_other_updates() -> None:
    assert audit_action_for({"name"}) == "product.updated"
    assert audit_action_for({"is_available", "price"}) == "product.updated"


# --- authorization branches ---


@pytest.mark.req("S-1")
async def test_update_store_by_non_owner_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(owner_id=PydanticObjectId())  # owned by someone else
    intruder = _user(Role.CLIENT)
    monkeypatch.setattr(stores_service.stores_repo, "get_by_id", _returns(store))

    with pytest.raises(AppError) as exc:
        await stores_service.update_store(intruder, PydanticObjectId(), StoreUpdate(name="Hacked"))
    assert exc.value.status_code == 403


@pytest.mark.req("S-1")
async def test_suspend_requires_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = _user(Role.SELLER)
    store = _store(owner_id=owner.id)
    monkeypatch.setattr(stores_service.stores_repo, "get_by_id", _returns(store))

    with pytest.raises(AppError) as exc:
        await stores_service.set_status(
            owner, PydanticObjectId(), StoreStatusUpdate(status=StoreStatus.SUSPENDED)
        )
    assert exc.value.status_code == 403


@pytest.mark.req("S-3")
async def test_create_product_by_non_owner_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(owner_id=PydanticObjectId())
    intruder = _user(Role.CLIENT)
    monkeypatch.setattr(catalog_service.stores_repo, "get_by_id", _returns(store))

    with pytest.raises(AppError) as exc:
        await catalog_service.create_product(
            intruder, PydanticObjectId(), ProductCreate(name="X", price=100)
        )
    assert exc.value.status_code == 403
