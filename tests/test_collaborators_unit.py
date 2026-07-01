"""Unit tests for collaborator logic (no DB): availability + geo query + authz."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.collaborators import service as collab_service
from app.collaborators.models import Availability, VehicleType, VerificationStatus
from app.collaborators.repository import build_available_near_query
from app.collaborators.schemas import AvailabilityUpdate, BecomeCollaborator
from app.collaborators.service import resolve_availability
from app.core.errors import AppError


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("D-2")
def test_resolve_availability_online_requires_coords() -> None:
    ok, loc = resolve_availability(
        AvailabilityUpdate(status=Availability.ONLINE, lng=-74.0, lat=4.6)
    )
    assert ok == Availability.ONLINE
    assert loc is not None and loc.coordinates == (-74.0, 4.6)

    with pytest.raises(AppError) as exc:
        resolve_availability(AvailabilityUpdate(status=Availability.ONLINE))
    assert exc.value.status_code == 422
    assert exc.value.code == "location_required"


@pytest.mark.req("D-2")
def test_resolve_availability_offline_and_invalid() -> None:
    ok, loc = resolve_availability(AvailabilityUpdate(status=Availability.OFFLINE))
    assert ok == Availability.OFFLINE and loc is None

    with pytest.raises(AppError) as exc:
        resolve_availability(AvailabilityUpdate(status=Availability.ON_DELIVERY))
    assert exc.value.code == "invalid_status"


@pytest.mark.req("D-1")
def test_available_near_query() -> None:
    q = build_available_near_query((-74.0, 4.6), 3000)
    assert q["verification_status"] == VerificationStatus.APPROVED.value
    assert q["availability"] == Availability.ONLINE.value
    assert q["current_location"]["$near"]["$maxDistance"] == 3000


@pytest.mark.req("D-2")
async def test_cannot_go_online_when_not_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[])
    profile = SimpleNamespace(verification_status=VerificationStatus.PENDING)
    monkeypatch.setattr(collab_service.collab_repo, "get_by_user_id", _returns(profile))

    with pytest.raises(AppError) as exc:
        await collab_service.set_availability(
            user, AvailabilityUpdate(status=Availability.ONLINE, lng=-74.0, lat=4.6)
        )
    assert exc.value.status_code == 403
    assert exc.value.code == "not_approved"


@pytest.mark.req("U-5")
async def test_become_collaborator_twice_conflicts(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[])
    monkeypatch.setattr(collab_service.collab_repo, "get_by_user_id", _returns(object()))

    with pytest.raises(AppError) as exc:
        await collab_service.become_collaborator(
            user, BecomeCollaborator(vehicle_type=VehicleType.BIKE, id_number="123456")
        )
    assert exc.value.status_code == 409
