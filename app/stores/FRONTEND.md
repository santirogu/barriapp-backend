# Stores — Frontend & Mobile Contract

> Contract for the **implemented** stores endpoints (source of truth: `app/stores`).

## Context
A **store** is a seller's shop (tienda de barrio). Any authenticated user can
create one; creating the first store grants the `seller` role (become-seller).
Stores are discoverable by **proximity** (map/list "near me"), category, and name.
Owners manage their store; suspension is admin-only.

## Enums
- `status`: `open` | `closed` | `suspended`
  - `open`/`closed` toggled by the owner; a closed store stays discoverable but
    takes no orders. `suspended` is set by an admin (moderation) and hides/blocks it.

## Geo format (important)
GeoJSON, coordinates are **`[longitude, latitude]`** (not lat,lng):
```json
{ "type": "Point", "coordinates": [-74.081, 4.609] }
```

## Models
`StoreLocation`: `{ "line": "Cra 10 #20-30", "city": "Bogotá"?, "geo": <GeoPoint> }`
`Schedule`: `{ "timezone": "America/Bogota", "days": { "mon": [{"open":"08:00","close":"20:00"}], ... } }`
`DeliveryConfig`: `{ "radius_meters": 2000, "base_fee": 0, "min_order": 0, "free_over": null }` (COP)
`Rating`: `{ "avg": 0.0, "count": 0 }`

`StorePublic`:
```json
{
  "id": "665f...", "owner_id": "665e...",
  "name": "Tienda Ana", "description": null,
  "logo_url": null, "cover_url": null,
  "category_ids": [],
  "location": { "line": "Cra 10", "city": null, "geo": {"type":"Point","coordinates":[-74.081,4.609]} },
  "schedule": { "timezone": "America/Bogota", "days": {} },
  "status": "closed",
  "delivery": { "radius_meters": 2000, "base_fee": 0, "min_order": 0, "free_over": null },
  "rating": { "avg": 0.0, "count": 0 }
}
```

## Endpoints

### POST `/api/v1/stores`  (auth)
Create a store; grants the `seller` role on the first one. Store starts `closed`.
Request (`StoreCreate`):
```json
{ "name": "Tienda Ana",
  "location": { "line": "Cra 10 #20-30", "geo": {"type":"Point","coordinates":[-74.081,4.609]} },
  "description": null, "schedule": null, "delivery": null, "category_ids": [] }
```
Response `201`: `StorePublic`. Errors: `401 not_authenticated`, `422 validation_error`.

### GET `/api/v1/stores`  (public) — search / discovery
Query params:
- `near` = `"lng,lat"` (optional; enables nearest-first geo search)
- `radius` = meters (default `5000`, 1–50000)
- `category` = category id (optional)
- `q` = name substring, case-insensitive (optional)
- `page` (default 1), `limit` (default 20, max 100)

Returns `StorePublic[]` (suspended stores excluded; nearest-first when `near` set).
Example: `GET /api/v1/stores?near=-74.081,4.609&radius=3000&q=tienda`.
Errors: `422 invalid_query` (bad `near`/`category`).

### GET `/api/v1/stores/{id}`  (public)
Returns `StorePublic`. Errors: `404 not_found`.

### PATCH `/api/v1/stores/{id}`  (auth, owner or admin)
Partial update (`StoreUpdate`): any of `name`, `description`, `logo_url`,
`cover_url`, `location`, `schedule`, `delivery`.
Response `200`: `StorePublic`. Errors: `403 forbidden` (not owner), `404 not_found`.

### PATCH `/api/v1/stores/{id}/status`  (auth)
Body: `{ "status": "open" | "closed" | "suspended" }`.
- Owner may set `open`/`closed`; **only an admin** may set/lift `suspended`.
Response `200`: `StorePublic`. Errors: `403 forbidden`, `404 not_found`.

## Notes for the client
- Products for a store come from the **catalog** module: `GET /stores/{id}/products`
  (see `app/catalog/FRONTEND.md`).
- Money fields (`base_fee`, `min_order`, `free_over`) are integer **COP**.
- For a map screen, request with `near` and render nearest-first; paginate with
  `page`/`limit`.
