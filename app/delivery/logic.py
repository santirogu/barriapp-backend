"""Pure delivery logic (no DB): status transitions and order-status sync."""

from app.delivery.models import DeliveryStatus
from app.orders.models import OrderStatus

# Forward-only delivery transitions the collaborator drives.
DELIVERY_ADVANCE: dict[DeliveryStatus, DeliveryStatus] = {
    DeliveryStatus.ASSIGNED: DeliveryStatus.EN_ROUTE_PICKUP,
    DeliveryStatus.EN_ROUTE_PICKUP: DeliveryStatus.PICKED_UP,
    DeliveryStatus.PICKED_UP: DeliveryStatus.EN_ROUTE_DROPOFF,
    DeliveryStatus.EN_ROUTE_DROPOFF: DeliveryStatus.DELIVERED,
}

# Delivery milestones that move the underlying order forward.
_ORDER_SYNC: dict[DeliveryStatus, OrderStatus] = {
    DeliveryStatus.PICKED_UP: OrderStatus.PICKED_UP,
    DeliveryStatus.DELIVERED: OrderStatus.DELIVERED,
}


def next_delivery_status(current: DeliveryStatus) -> DeliveryStatus | None:
    return DELIVERY_ADVANCE.get(current)


def order_status_for(delivery_status: DeliveryStatus) -> OrderStatus | None:
    """The order status a delivery milestone should sync to (or None)."""
    return _ORDER_SYNC.get(delivery_status)
