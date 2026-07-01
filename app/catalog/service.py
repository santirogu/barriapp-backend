"""Catalog business logic: categories and products (with store-ownership checks)."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import status

from app.audit import service as audit
from app.audit.models import AuditModule
from app.catalog import repository as catalog_repo
from app.catalog.models import Category, CategoryType, Product
from app.catalog.schemas import CategoryCreate, ProductCreate, ProductUpdate
from app.core.errors import AppError
from app.stores import repository as stores_repo
from app.users.models import Role, User
from app.users.service import primary_role


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_admin(user: User) -> bool:
    return Role.SUPER_ADMIN in user.roles


def audit_action_for(changed_fields: set[str]) -> str:
    """Pick the audit action for a product update (pure; unit-tested)."""
    if changed_fields == {"is_available"}:
        return "product.availability.changed"
    return "product.updated"


async def _assert_store_owner(user: User, store_id: PydanticObjectId) -> None:
    store = await stores_repo.get_by_id(store_id)
    if store is None:
        raise AppError("Store not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
    if store.owner_id != user.id and not _is_admin(user):
        raise AppError(
            "Not the store owner", code="forbidden", status_code=status.HTTP_403_FORBIDDEN
        )


# --- categories ---


async def list_categories(category_type: CategoryType | None) -> list[Category]:
    return await catalog_repo.list_categories(category_type)


async def create_category(user: User, data: CategoryCreate) -> Category:
    category = Category(
        name=data.name,
        slug=data.slug,
        type=data.type,
        icon=data.icon,
        parent_id=PydanticObjectId(data.parent_id) if data.parent_id else None,
    )
    await catalog_repo.insert_category(category)
    await audit.record(
        module=AuditModule.CATALOG,
        action="category.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="category",
        target_id=category.id,
    )
    return category


# --- products ---


async def get_product(product_id: PydanticObjectId) -> Product:
    product = await catalog_repo.get_product(product_id)
    if product is None:
        raise AppError("Product not found", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
    return product


async def list_products(store_id: PydanticObjectId, *, available_only: bool) -> list[Product]:
    return await catalog_repo.list_products_by_store(store_id, available_only=available_only)


async def create_product(user: User, store_id: PydanticObjectId, data: ProductCreate) -> Product:
    await _assert_store_owner(user, store_id)
    product = Product(
        store_id=store_id,
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        category_id=PydanticObjectId(data.category_id) if data.category_id else None,
        price=data.price,
        compare_at_price=data.compare_at_price,
        stock=data.stock,
        unit=data.unit,
        tags=data.tags,
    )
    await catalog_repo.insert_product(product)
    await audit.record(
        module=AuditModule.CATALOG,
        action="product.created",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="product",
        target_id=product.id,
    )
    return product


async def update_product(user: User, product_id: PydanticObjectId, data: ProductUpdate) -> Product:
    product = await get_product(product_id)
    await _assert_store_owner(user, product.store_id)

    fields = data.model_dump(exclude_unset=True)
    for field, value in fields.items():
        if field == "category_id":
            value = PydanticObjectId(value) if value else None
        setattr(product, field, value)

    if fields:
        product.updated_at = _utcnow()
        await product.save()
        await audit.record(
            module=AuditModule.CATALOG,
            action=audit_action_for(set(fields)),
            actor_id=user.id,
            actor_role=primary_role(user),
            target_type="product",
            target_id=product.id,
            changes={"updated_fields": sorted(fields)},
        )
    return product


async def delete_product(user: User, product_id: PydanticObjectId) -> None:
    product = await get_product(product_id)
    await _assert_store_owner(user, product.store_id)
    await product.delete()
    await audit.record(
        module=AuditModule.CATALOG,
        action="product.deleted",
        actor_id=user.id,
        actor_role=primary_role(user),
        target_type="product",
        target_id=product_id,
    )
