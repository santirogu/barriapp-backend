"""Unit tests for pure order logic (no DB): amounts, transitions, code (O-1, O-6)."""

import re

import pytest

from app.orders.logic import (
    can_cancel,
    compute_amounts,
    generate_order_code,
    next_seller_status,
)
from app.orders.models import OrderStatus


@pytest.mark.req("O-1")
def test_compute_amounts_basic() -> None:
    a = compute_amounts(items_total=7000, base_fee=2000, free_over=None, commission_rate=0.10)
    assert a.items_total == 7000
    assert a.delivery_fee == 2000
    assert a.platform_fee == 700  # 10% of items
    assert a.discount == 0
    assert a.total == 9000  # items + delivery


@pytest.mark.req("O-1")
def test_compute_amounts_free_delivery_over_threshold() -> None:
    a = compute_amounts(items_total=50000, base_fee=3000, free_over=40000, commission_rate=0.12)
    assert a.delivery_fee == 0  # items_total >= free_over
    assert a.platform_fee == 6000
    assert a.total == 50000


@pytest.mark.req("O-3")
def test_seller_status_transitions() -> None:
    assert next_seller_status(OrderStatus.ACCEPTED) == OrderStatus.PREPARING
    assert next_seller_status(OrderStatus.PREPARING) == OrderStatus.READY
    assert next_seller_status(OrderStatus.PENDING) is None  # accept is separate
    assert next_seller_status(OrderStatus.READY) is None


@pytest.mark.req("O-4")
def test_can_cancel_rules() -> None:
    assert can_cancel(OrderStatus.PENDING)
    assert can_cancel(OrderStatus.READY)
    assert not can_cancel(OrderStatus.PICKED_UP)
    assert not can_cancel(OrderStatus.DELIVERED)
    assert not can_cancel(OrderStatus.CANCELLED)


@pytest.mark.req("O-1")
def test_order_code_format() -> None:
    code = generate_order_code()
    assert re.fullmatch(r"BA-[0-9A-F]{8}", code)
    assert generate_order_code() != generate_order_code()  # random
