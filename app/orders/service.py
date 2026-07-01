"""Orders business logic: creation (totals + commission + stock), lifecycle."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.catalog import repository as catalog_repo
from app.catalog.models import Product
from app.core.config import get_settings
from app.core.errors import AppError
from app.notifications import service as notifications_service
from app.notifications.models import NotificationType
from app.orders import logic
from app.orders import repository as orders_repo
from app.orders.models import Order, OrderItem, OrderStatus, StatusEvent
from app.orders.schemas import OrderCancel, OrderCreate, OrderStatusUpdate
from app.stores import repository as stores_repo
from app.stores.models import Store, StoreStatus
from app.users.models import Role, User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_admin(user: User) -> bool:
    return Role.SUPER_ADMIN in user.roles


def _not_found() -> AppError:
    return AppError("Order not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)


async def _load_order(order_id: PydanticObjectId) -> Order:
    order = await orders_repo.get_by_id(order_id)
    if order is None:
        raise _not_found()
    return order


async def _load_store(store_id: PydanticObjectId) -> Store:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
    return store


def _record_status(order: Order, new_status: OrderStatus, by: PydanticObjectId | None) -> None:
    order.status = new_status
    order.status_history.append(StatusEvent(status=new_status, at=_utcnow(), by=by))
    order.updated_at = _utcnow()


async def create_order(user: User, data: OrderCreate) -> Order:
    store = await _load_store(PydanticObjectId(data.store_id))
    if store.status == StoreStatus.SUSPENDED:
        raise AppError("Store unavailable", code="store_unavailable", status_code=409)
    if store.status != StoreStatus.OPEN:
        raise AppError("Store is not open", code="store_not_open", status_code=409)

    # Validate items, snapshot prices, and prepare stock decrements.
    items: list[OrderItem] = []
    to_decrement: list[tuple[Product, int]] = []
    for line in data.items:
        product = await catalog_repo.get_product(PydanticObjectId(line.product_id))
        if product is None or product.store_id != store.id:
            raise AppError(
                f"Product {line.product_id} not in this store",
                code="invalid_product",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not product.is_available:
            raise AppError(
                f"Product {product.name} is unavailable",
                code="product_unavailable",
                status_code=409,
            )
        if product.stock is not None and line.qty > product.stock:
            raise AppError(
                f"Insufficient stock for {product.name}",
                code="insufficient_stock",
                status_code=409,
            )
        items.append(
            OrderItem(
                product_id=product.id,
                name=product.name,
                price=product.price,
                qty=line.qty,
                subtotal=product.price * line.qty,
            )
        )
        if product.stock is not None:
            to_decrement.append((product, line.qty))

    items_total = sum(item.subtotal for item in items)
    if items_total < store.delivery.min_order:
        raise AppError(
            "Order below the store minimum",
            code="below_min_order",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    rate = (
        store.commission_rate
        if store.commission_rate is not None
        else get_settings().default_commission_rate
    )
    amounts = logic.compute_amounts(
        items_total=items_total,
        base_fee=store.delivery.base_fee,
        free_over=store.delivery.free_over,
        commission_rate=rate,
    )

    # Commit stock decrements now that validation passed.
    for product, qty in to_decrement:
        product.stock = (product.stock or 0) - qty
        await product.save()

    order = Order(
        code=logic.generate_order_code(),
        client_id=user.id,
        store_id=store.id,
        items=items,
        amounts=amounts,
        delivery_address=data.delivery_address,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    _record_status(order, OrderStatus.PENDING, user.id)
    await orders_repo.insert(order)

    await audit.record(
        module=AuditModule.ORDERS,
        action="order.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="order",
        target_id=order.id,
        changes={"store_id": str(store.id), "total": amounts.total},
    )
    return order


async def get_order(user: User, order_id: PydanticObjectId) -> Order:
    order = await _load_order(order_id)
    if _is_admin(user) or user.id in (order.client_id, order.collaborator_id):
        return order
    store = await stores_repo.get_by_id(order.store_id)
    if store is not None and store.owner_id == user.id:
        return order
    raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)


async def list_my_orders(user: User, *, skip: int, limit: int) -> list[Order]:
    assert user.id is not None  # a persisted, authenticated user always has an id
    return await orders_repo.list_by_client(user.id, skip=skip, limit=limit)


async def _assert_store_owner(user: User, order: Order) -> Store:
    store = await _load_store(order.store_id)
    if store.owner_id != user.id and not _is_admin(user):
        raise AppError(
            "Not the store owner", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )
    return store


async def accept_order(user: User, order_id: PydanticObjectId) -> Order:
    order = await _load_order(order_id)
    await _assert_store_owner(user, order)
    if order.status != OrderStatus.PENDING:
        raise AppError("Order cannot be accepted", code="invalid_transition", status_code=409)
    _record_status(order, OrderStatus.ACCEPTED, user.id)
    await order.save()
    await audit.record(
        module=AuditModule.ORDERS,
        action="order.accepted",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="order",
        target_id=order.id,
    )
    await notifications_service.notify(
        user_id=order.client_id,
        type=NotificationType.ORDER_UPDATE,
        title="Pedido aceptado",
        body=f"La tienda aceptó tu pedido {order.code}.",
        data={"order_id": str(order.id), "status": OrderStatus.ACCEPTED.value},
    )
    return order


async def advance_status(user: User, order_id: PydanticObjectId, data: OrderStatusUpdate) -> Order:
    order = await _load_order(order_id)
    await _assert_store_owner(user, order)
    if logic.next_seller_status(order.status) != data.status:
        raise AppError(
            f"Cannot move from {order.status} to {data.status}",
            code="invalid_transition",
            status_code=409,
        )
    previous = order.status
    _record_status(order, data.status, user.id)
    await order.save()
    await audit.record(
        module=AuditModule.ORDERS,
        action="order.status.changed",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="order",
        target_id=order.id,
        changes={"before": str(previous), "after": str(data.status)},
    )
    await notifications_service.notify(
        user_id=order.client_id,
        type=NotificationType.ORDER_UPDATE,
        title="Pedido actualizado",
        body=f"Tu pedido {order.code} está {data.status.value}.",
        data={"order_id": str(order.id), "status": data.status.value},
    )
    return order


async def cancel_order(user: User, order_id: PydanticObjectId, data: OrderCancel) -> Order:
    order = await _load_order(order_id)

    is_client = order.client_id == user.id
    store = await stores_repo.get_by_id(order.store_id)
    is_owner = store is not None and store.owner_id == user.id
    if not (is_client or is_owner or _is_admin(user)):
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)

    if not logic.can_cancel(order.status):
        raise AppError(
            f"Order in status {order.status} cannot be cancelled",
            code="invalid_transition",
            status_code=409,
        )

    # Restore stock for tracked products.
    for item in order.items:
        product = await catalog_repo.get_product(item.product_id)
        if product is not None and product.stock is not None:
            product.stock = product.stock + item.qty
            await product.save()

    _record_status(order, OrderStatus.CANCELLED, user.id)
    await order.save()
    await audit.record(
        module=AuditModule.ORDERS,
        action="order.cancelled",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="order",
        target_id=order.id,
        changes={"reason": data.reason},
    )
    return order
