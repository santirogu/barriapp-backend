"""Unit tests for delivery logic (no DB): transitions, order sync, authz."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.delivery import service as delivery_service
from app.delivery.logic import next_delivery_status, order_status_for
from app.delivery.models import DeliveryStatus
from app.delivery.schemas import DeliveryStatusUpdate
from app.orders.models import OrderStatus
from app.users.models import Role


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("D-3")
def test_delivery_transitions() -> None:
    assert next_delivery_status(DeliveryStatus.ASSIGNED) == DeliveryStatus.EN_ROUTE_PICKUP
    assert next_delivery_status(DeliveryStatus.EN_ROUTE_PICKUP) == DeliveryStatus.PICKED_UP
    assert next_delivery_status(DeliveryStatus.PICKED_UP) == DeliveryStatus.EN_ROUTE_DROPOFF
    assert next_delivery_status(DeliveryStatus.EN_ROUTE_DROPOFF) == DeliveryStatus.DELIVERED
    assert next_delivery_status(DeliveryStatus.DELIVERED) is None


@pytest.mark.req("D-3")
def test_order_status_sync() -> None:
    assert order_status_for(DeliveryStatus.PICKED_UP) == OrderStatus.PICKED_UP
    assert order_status_for(DeliveryStatus.DELIVERED) == OrderStatus.DELIVERED
    assert order_status_for(DeliveryStatus.EN_ROUTE_PICKUP) is None
    assert order_status_for(DeliveryStatus.ASSIGNED) is None


@pytest.mark.req("D-3")
async def test_advance_by_non_assigned_collaborator_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), role=Role.CLIENT)
    delivery = SimpleNamespace(
        collaborator_id=PydanticObjectId(),  # someone else
        status=DeliveryStatus.ASSIGNED,
    )
    monkeypatch.setattr(delivery_service.delivery_repo, "get_by_id", _returns(delivery))

    with pytest.raises(AppError) as exc:
        await delivery_service.advance_status(
            user, PydanticObjectId(), DeliveryStatusUpdate(status=DeliveryStatus.EN_ROUTE_PICKUP)
        )
    assert exc.value.status_code == 403
    assert exc.value.code == "forbidden"
