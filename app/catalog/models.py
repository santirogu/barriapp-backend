"""Catalog models: categories and per-store products. See docs/DATA_MODEL.md §3.4-3.5."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class CategoryType(StrEnum):
    STORE = "store"
    PRODUCT = "product"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Category(Document):
    name: str
    slug: str
    type: CategoryType
    icon: str | None = None
    parent_id: PydanticObjectId | None = None

    class Settings:
        name = "categories"
        indexes = [  # noqa: RUF012
            IndexModel("slug", unique=True),
            IndexModel("type"),
        ]


class Product(Document):
    store_id: PydanticObjectId
    name: str
    description: str | None = None
    image_url: str | None = None
    category_id: PydanticObjectId | None = None
    price: int  # COP
    compare_at_price: int | None = None  # COP
    stock: int | None = None  # None = not stock-tracked
    unit: str = "und"
    is_available: bool = True
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "products"
        indexes = [  # noqa: RUF012
            IndexModel([("store_id", 1), ("category_id", 1)]),
            IndexModel([("store_id", 1), ("is_available", 1)]),
            IndexModel([("name", "text"), ("tags", "text")]),
        ]
