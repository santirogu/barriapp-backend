"""Unit tests for review logic (no DB): rating recompute + authz."""

from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.orders.models import OrderStatus
from app.reviews import service as reviews_service
from app.reviews.logic import recompute_rating
from app.reviews.models import ReviewTargetType
from app.reviews.schemas import ReviewCreate


def _returns(value: object):
    async def _inner(*_a: object, **_k: object) -> object:
        return value

    return _inner


@pytest.mark.req("R-1")
def test_recompute_rating() -> None:
    assert recompute_rating(0.0, 0, 5) == (5.0, 1)
    assert recompute_rating(4.0, 2, 5) == (4.33, 3)
    assert recompute_rating(5.0, 1, 3) == (4.0, 2)


@pytest.mark.req("R-1")
async def test_review_requires_delivered_order(monkeypatch: pytest.MonkeyPatch) -> None:
    uid = PydanticObjectId()
    user = SimpleNamespace(id=uid, roles=[])
    order = SimpleNamespace(client_id=uid, status=OrderStatus.PENDING)
    monkeypatch.setattr(reviews_service.orders_repo, "get_by_id", _returns(order))

    with pytest.raises(AppError) as exc:
        await reviews_service.create_review(
            user,
            ReviewCreate(
                order_id=str(PydanticObjectId()), target_type=ReviewTargetType.STORE, stars=5
            ),
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "not_delivered"


@pytest.mark.req("R-1")
async def test_review_only_by_order_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=PydanticObjectId(), roles=[])
    order = SimpleNamespace(client_id=PydanticObjectId(), status=OrderStatus.DELIVERED)
    monkeypatch.setattr(reviews_service.orders_repo, "get_by_id", _returns(order))

    with pytest.raises(AppError) as exc:
        await reviews_service.create_review(
            user,
            ReviewCreate(
                order_id=str(PydanticObjectId()), target_type=ReviewTargetType.STORE, stars=5
            ),
        )
    assert exc.value.status_code == 403
