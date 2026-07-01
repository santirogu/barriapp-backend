# Catalog — Frontend & Mobile Contract

> Contract for the **implemented** catalog endpoints (source of truth: `app/catalog`).

## Context
The catalog is **categories** (reference data, admin-managed) and **products**
(per store, managed by the store owner). Clients browse a store's products; owners
create/edit/delete their products and toggle availability for the common
"se acabó" (out of stock) case.

## Enums
- `category.type`: `store` | `product`

## Money & stock
- `price` and `compare_at_price` are integer **COP** (e.g. `3500` = COP $3,500).
- `stock`: integer, or `null` = the store does not track stock for that product.
- `is_available`: quick on/off flag independent of stock (use for out-of-stock UX).

## Models
`CategoryPublic`:
```json
{ "id": "665f...", "name": "Bebidas", "slug": "bebidas", "type": "product", "icon": null }
```
`ProductPublic`:
```json
{
  "id": "665f...", "store_id": "665e...",
  "name": "Arroz 500g", "description": null, "image_url": null,
  "category_id": null,
  "price": 3500, "compare_at_price": null,
  "stock": null, "unit": "und",
  "is_available": true, "tags": []
}
```

## Endpoints — categories

### GET `/api/v1/categories`  (public)
Optional query `type` = `store` | `product`. Returns `CategoryPublic[]`.

### POST `/api/v1/categories`  (super_admin)
Request (`CategoryCreate`): `{ "name": "Bebidas", "slug": "bebidas", "type": "product", "icon": null, "parent_id": null }`
Response `201`: `CategoryPublic`. Errors: `401 not_authenticated`, `403 forbidden`.

## Endpoints — products

### POST `/api/v1/stores/{store_id}/products`  (auth, store owner)
Request (`ProductCreate`):
```json
{ "name": "Arroz 500g", "price": 3500, "unit": "und",
  "description": null, "image_url": null, "category_id": null,
  "compare_at_price": null, "stock": null, "tags": [] }
```
Response `201`: `ProductPublic`. Errors: `403 forbidden` (not the store owner),
`404 not_found` (store), `422 validation_error`.

### GET `/api/v1/stores/{store_id}/products`  (public)
Optional query `available_only` (bool, default `false`). Returns `ProductPublic[]`.
Use `available_only=true` for the customer-facing catalog.

### GET `/api/v1/products/{id}`  (public)
Returns `ProductPublic`. Errors: `404 not_found`.

### PATCH `/api/v1/products/{id}`  (auth, store owner)
Partial update (`ProductUpdate`): any of `name`, `description`, `image_url`,
`category_id`, `price`, `compare_at_price`, `stock`, `unit`, `is_available`, `tags`.
Response `200`: `ProductPublic`. Errors: `403 forbidden`, `404 not_found`.
Tip: toggling only `is_available` is the fast "out of stock" action.

### DELETE `/api/v1/products/{id}`  (auth, store owner)
Response `204`. Errors: `403 forbidden`, `404 not_found`.

## Notes for the client
- Product ownership is derived from its store; the API enforces it (non-owners get
  `403 forbidden`). The UI should only show edit controls to the store owner.
- Prices are integers in COP — format on the client (e.g. `3.500`).
