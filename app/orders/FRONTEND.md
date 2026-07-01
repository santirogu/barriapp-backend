# Orders — Frontend & Mobile Contract

> Contract for the **implemented** orders endpoints (source of truth: `app/orders`).
> See also `docs/ORDER_FLOW.md` for the full lifecycle.

## Context
A client places an order to a store: pick items from the store's catalog, provide
a delivery address and a payment method. The backend snapshots item prices,
computes totals + platform commission, and decrements stock. The seller then moves
the order `accepted → preparing → ready`. Assignment to a collaborator and live
tracking are a later module (`delivery`).

## Enums
- `status`: `pending` → `accepted` → `preparing` → `ready` → `assigned` →
  `picked_up` → `delivered`, or `cancelled`. (This module implements
  `pending…ready` + `cancelled`; the rest arrive with `delivery`.)
- `payment_method`: `cash` | `wompi` (only the method is recorded here; Wompi
  charging is handled by the future `payments` module).

## Money (all integer COP)
`amounts`: `{ items_total, delivery_fee, platform_fee, discount, total }`.
- The client pays **`total` = items_total + delivery_fee − discount**.
- `platform_fee` is the commission withheld from the seller (informational for the client).

## Models
`OrderItem` (snapshot): `{ product_id, name, price, qty, subtotal }`.
`StatusEvent`: `{ status, at (ISO-8601), by (user id|null) }`.
`OrderPublic`:
```json
{
  "id": "665f...", "code": "BA-1A2B3C4D",
  "client_id": "665e...", "store_id": "665d...",
  "items": [{"product_id":"665c...","name":"Arroz 500g","price":3500,"qty":2,"subtotal":7000}],
  "amounts": {"items_total":7000,"delivery_fee":0,"platform_fee":700,"discount":0,"total":7000},
  "delivery_address": {"label":"Casa","line":"Cra 9 #1-1","geo":{"type":"Point","coordinates":[-74.081,4.609]}},
  "status": "pending",
  "status_history": [{"status":"pending","at":"2026-07-01T12:00:00Z","by":"665e..."}],
  "payment_method": "cash",
  "collaborator_id": null,
  "notes": null,
  "created_at": "2026-07-01T12:00:00Z"
}
```

## Endpoints

### POST `/api/v1/orders`  (auth — client)
Create an order. Request (`OrderCreate`):
```json
{ "store_id": "665d...",
  "items": [{"product_id": "665c...", "qty": 2}],
  "delivery_address": {"label":"Casa","line":"Cra 9 #1-1","geo":{"type":"Point","coordinates":[-74.081,4.609]}},
  "payment_method": "cash",
  "notes": null }
```
Response `201`: `OrderPublic` (status `pending`).
Errors: `404 not_found` (store), `409 store_not_open`, `409 store_unavailable`,
`422 invalid_product` (not in store), `409 product_unavailable`,
`409 insufficient_stock`, `422 below_min_order`.

### GET `/api/v1/orders`  (auth — client)
Query `page` (default 1), `limit` (default 20, max 100). Returns the caller's
`OrderPublic[]`, newest first.

### GET `/api/v1/orders/{id}`  (auth — client, store owner, assigned collaborator, or admin)
Returns `OrderPublic`. Errors: `403 forbidden`, `404 not_found`.

### POST `/api/v1/orders/{id}/accept`  (auth — store owner)
`pending → accepted`. Errors: `403 forbidden`, `409 invalid_transition`, `404 not_found`.

### POST `/api/v1/orders/{id}/status`  (auth — store owner)
Body `{ "status": "preparing" | "ready" }`. Only the next valid step is allowed
(`accepted→preparing→ready`). Errors: `409 invalid_transition`, `403 forbidden`.

### POST `/api/v1/orders/{id}/cancel`  (auth — client, store owner, or admin)
Body `{ "reason": "optional text" }`. Allowed before pickup
(`pending/accepted/preparing/ready`); restores stock. Response `200`: `OrderPublic`
(status `cancelled`). Errors: `409 invalid_transition`, `403 forbidden`.

## Notes for the client
- Build the cart from `GET /stores/{id}/products?available_only=true`, then send
  `product_id` + `qty`. Prices/totals are authoritative from the server response —
  render `amounts` rather than recomputing.
- Poll `GET /orders/{id}` (or the future tracking WebSocket) to reflect status.
- `code` (e.g. `BA-1A2B3C4D`) is the human-facing order reference.

## Not yet implemented (planned)
Collaborator assignment (`/orders/{id}/assign`), delivery/tracking, and Wompi
payment intents live in the upcoming `delivery` and `payments` modules
(see `docs/API_CONTRACT.md` §6/§8/§10 and `docs/ORDER_FLOW.md`).
