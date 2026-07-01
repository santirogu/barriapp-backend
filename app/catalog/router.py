"""Catalog endpoints (categories and products). See docs/API_CONTRACT.md §4-5."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, status

from app.catalog import service
from app.catalog.models import CategoryType
from app.catalog.schemas import (
    CategoryCreate,
    CategoryPublic,
    ProductCreate,
    ProductPublic,
    ProductUpdate,
)
from app.core.deps import CurrentUser, require_roles
from app.users.models import Role, User

router = APIRouter(tags=["catalog"])

AdminUser = Annotated[User, Depends(require_roles(Role.SUPER_ADMIN))]


@router.get("/categories", response_model=list[CategoryPublic])
async def list_categories(type: CategoryType | None = Query(None)) -> list[CategoryPublic]:
    categories = await service.list_categories(type)
    return [CategoryPublic.from_category(c) for c in categories]


@router.post("/categories", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, user: AdminUser) -> CategoryPublic:
    return CategoryPublic.from_category(await service.create_category(user, data))


@router.post(
    "/stores/{store_id}/products",
    response_model=ProductPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    store_id: PydanticObjectId, data: ProductCreate, user: CurrentUser
) -> ProductPublic:
    return ProductPublic.from_product(await service.create_product(user, store_id, data))


@router.get("/stores/{store_id}/products", response_model=list[ProductPublic])
async def list_products(
    store_id: PydanticObjectId,
    available_only: bool = Query(False),
) -> list[ProductPublic]:
    products = await service.list_products(store_id, available_only=available_only)
    return [ProductPublic.from_product(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductPublic)
async def get_product(product_id: PydanticObjectId) -> ProductPublic:
    return ProductPublic.from_product(await service.get_product(product_id))


@router.patch("/products/{product_id}", response_model=ProductPublic)
async def update_product(
    product_id: PydanticObjectId, data: ProductUpdate, user: CurrentUser
) -> ProductPublic:
    return ProductPublic.from_product(await service.update_product(user, product_id, data))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: PydanticObjectId, user: CurrentUser) -> None:
    await service.delete_product(user, product_id)
