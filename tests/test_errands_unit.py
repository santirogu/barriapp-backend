"""Unit tests for errand logic (no DB): transitions, cancel, code, geo, authz."""

import re
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.errands import service as errands_service
from app.errands.logic import (
    build_available_query,
    can_cancel,
    generate_errand_code,
    next_status,
)
from app.errands.models import ErrandStatus
from app.errands.schemas import ErrandStatusUpdate
from app.users.models import Role


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("E-3")
def test_transitions_and_cancel_rules() -> None:
    assert next_status(ErrandStatus.ASSIGNED) == ErrandStatus.IN_PROGRESS
    assert next_status(ErrandStatus.IN_PROGRESS) == ErrandStatus.COMPLETED
    assert next_status(ErrandStatus.OPEN) is None
    assert can_cancel(ErrandStatus.OPEN)
    assert can_cancel(ErrandStatus.ASSIGNED)
    assert not can_cancel(ErrandStatus.IN_PROGRESS)
    assert not can_cancel(ErrandStatus.COMPLETED)


@pytest.mark.req("E-1")
def test_errand_code_format() -> None:
    assert re.fullmatch(r"MD-[0-9A-F]{8}", generate_errand_code())


@pytest.mark.req("E-2")
def test_available_query() -> None:
    q = build_available_query((-74.0, 4.6), 4000)
    assert q["status"] == ErrandStatus.OPEN.value
    assert q["dropoff.geo"]["$near"]["$maxDistance"] == 4000


@pytest.mark.req("E-3")
async def test_accept_requires_collaborator_role() -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[Role.CLIENT])
    with pytest.raises(AppError) as exc:
        await errands_service.accept(user, PydanticObjectId())
    assert exc.value.status_code == 403


@pytest.mark.req("E-3")
async def test_advance_by_non_assigned_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[Role.COLLABORATOR])
    errand = SimpleNamespace(collaborator_id=PydanticObjectId(), status=ErrandStatus.ASSIGNED)
    monkeypatch.setattr(errands_service.errands_repo, "get_by_id", _returns(errand))
    with pytest.raises(AppError) as exc:
        await errands_service.advance_status(
            user, PydanticObjectId(), ErrandStatusUpdate(status=ErrandStatus.IN_PROGRESS)
        )
    assert exc.value.status_code == 403
