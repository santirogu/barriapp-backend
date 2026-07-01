"""Pure order logic (no DB) — amounts, code generation, state transitions.

Kept side-effect-free so it can be unit-tested without a database.
"""

import secrets

from app.orders.models import OrderAmounts, OrderStatus

# Status advances a seller can drive (accept is handled separately).
SELLER_ADVANCE: dict[OrderStatus, OrderStatus] = {
    OrderStatus.ACCEPTED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.READY,
}

# Statuses from which an order may still be cancelled (before pickup).
CANCELLABLE: frozenset[OrderStatus] = frozenset(
    {
        OrderStatus.PENDING,
        OrderStatus.ACCEPTED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    }
)


def generate_order_code() -> str:
    return "BA-" + secrets.token_hex(4).upper()


def compute_amounts(
    *,
    items_total: int,
    base_fee: int,
    free_over: int | None,
    commission_rate: float,
    discount: int = 0,
) -> OrderAmounts:
    """Compute order amounts. The client pays items + delivery - discount; the
    platform fee is the commission withheld from the seller (not added on top)."""
    delivery_fee = 0 if (free_over is not None and items_total >= free_over) else base_fee
    platform_fee = round(items_total * commission_rate)
    total = items_total + delivery_fee - discount
    return OrderAmounts(
        items_total=items_total,
        delivery_fee=delivery_fee,
        platform_fee=platform_fee,
        discount=discount,
        total=total,
    )


def next_seller_status(current: OrderStatus) -> OrderStatus | None:
    return SELLER_ADVANCE.get(current)


def can_cancel(current: OrderStatus) -> bool:
    return current in CANCELLABLE
