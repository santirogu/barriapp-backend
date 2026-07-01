"""Data access for categories and products."""

from beanie import PydanticObjectId

from app.catalog.models import Category, CategoryType, Product


async def list_categories(category_type: CategoryType | None = None) -> list[Category]:
    criteria = {"type": category_type.value} if category_type is not None else {}
    return await Category.find(criteria).to_list()


async def insert_category(category: Category) -> Category:
    return await category.insert()


async def get_product(product_id: PydanticObjectId) -> Product | None:
    return await Product.get(product_id)


async def insert_product(product: Product) -> Product:
    return await product.insert()


async def list_products_by_store(
    store_id: PydanticObjectId, *, available_only: bool = False
) -> list[Product]:
    criteria: dict[str, object] = {"store_id": store_id}
    if available_only:
        criteria["is_available"] = True
    return await Product.find(criteria).to_list()
