"""Catalog I/O schemas."""

from pydantic import BaseModel, Field

from app.catalog.models import Category, CategoryType, Product


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80)
    type: CategoryType
    icon: str | None = None
    parent_id: str | None = None


class CategoryPublic(BaseModel):
    id: str
    name: str
    slug: str
    type: CategoryType
    icon: str | None

    @classmethod
    def from_category(cls, category: Category) -> "CategoryPublic":
        return cls(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            type=category.type,
            icon=category.icon,
        )


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    image_url: str | None = None
    category_id: str | None = None
    price: int = Field(ge=0)
    compare_at_price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    unit: str = "und"
    tags: list[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    image_url: str | None = None
    category_id: str | None = None
    price: int | None = Field(default=None, ge=0)
    compare_at_price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    unit: str | None = None
    is_available: bool | None = None
    tags: list[str] | None = None


class ProductPublic(BaseModel):
    id: str
    store_id: str
    name: str
    description: str | None
    image_url: str | None
    category_id: str | None
    price: int
    compare_at_price: int | None
    stock: int | None
    unit: str
    is_available: bool
    tags: list[str]

    @classmethod
    def from_product(cls, product: Product) -> "ProductPublic":
        return cls(
            id=str(product.id),
            store_id=str(product.store_id),
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            category_id=str(product.category_id) if product.category_id else None,
            price=product.price,
            compare_at_price=product.compare_at_price,
            stock=product.stock,
            unit=product.unit,
            is_available=product.is_available,
            tags=product.tags,
        )
