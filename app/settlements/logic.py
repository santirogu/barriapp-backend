"""Pure settlement logic (no DB)."""


def summarize_commissions(items: list[tuple[int, str]]) -> tuple[int, int]:
    """Given (amount, order_ref) pairs, return (total_commission, distinct_orders)."""
    total = sum(amount for amount, _ in items)
    orders = len({ref for _, ref in items})
    return total, orders
