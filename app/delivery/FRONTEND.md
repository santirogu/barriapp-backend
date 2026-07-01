# Delivery — Frontend & Mobile Contract

> Contract for the **implemented** delivery endpoints (source of truth:
> `app/delivery`). See `docs/ORDER_FLOW.md`. Requires collaborators (see
> `app/collaborators/FRONTEND.md`).

## Context
When an order is `ready`, the store (or an admin) **assigns** it: the backend picks
the nearest **approved + online** collaborator and creates a `Delivery`. The
collaborator then drives the delivery `assigned → en_route_pickup → picked_up →
en_route_dropoff → delivered`; picked_up/delivered sync the underlying order.
Location updates publish to Redis for live tracking.

## Enums
- `status`: `assigned` | `en_route_pickup` | `picked_up` | `en_route_dropoff` | `delivered`
- `ref_type`: `order` | `errand`

## Model — `DeliveryPublic`
```json
{
  "id": "665f...", "ref_type": "order", "ref_id": "665e...",
  "collaborator_id": "665d...",
  "status": "assigned",
  "route": [{"type":"Point","coordinates":[-74.08,4.61]}],
  "proof": null,
  "picked_up_at": null, "delivered_at": null,
  "created_at": "2026-07-01T12:00:00Z"
}
```

## Endpoints

### POST `/api/v1/orders/{order_id}/assign`  (auth — store owner or admin)
Assigns the nearest available collaborator. The order must be `ready`.
Response `201`: `DeliveryPublic` (status `assigned`); the order moves to `assigned`.
Errors: `403 forbidden`, `409 order_not_ready`, `409 already_assigned`,
`409 no_collaborator` (none online nearby), `404 not_found`.

### POST `/api/v1/deliveries/{id}/status`  (auth — assigned collaborator)
Body `{ "status": "<next>" }`. Only the next forward step is allowed. `picked_up`
sets the order to `picked_up`; `delivered` sets the order to `delivered` and frees
the collaborator (`online`). Errors: `403 forbidden`, `409 invalid_transition`.

### POST `/api/v1/deliveries/{id}/location`  (auth — assigned collaborator)
Body `{ "lng": -74.08, "lat": 4.61 }`. Appends a breadcrumb, updates the
collaborator's location, and publishes to `delivery:{id}` (Redis) for tracking.
**Throttle client-side** (e.g. every 5–10 s). Response `200`: `DeliveryPublic`.

### POST `/api/v1/deliveries/{id}/proof`  (auth — assigned collaborator)
Body `{ "photo_url": "https://...", "signature_url": null, "received_by": "Ana" }`.
Allowed at `en_route_dropoff` or `delivered`. Response `200`: `DeliveryPublic`.

### GET `/api/v1/deliveries/{id}`  (auth — collaborator, order client, store owner, or admin)
Returns `DeliveryPublic`. Errors: `403 forbidden`, `404 not_found`.

### GET `/api/v1/collaborator/jobs`  (auth — collaborator)
Query `page`/`limit`. Returns the caller's `DeliveryPublic[]`, newest first.

## Notes for the client
- **Client tracking:** poll `GET /deliveries/{id}` today; a **WebSocket**
  (`/ws/deliveries/{id}`) is planned next and will stream the Redis updates that
  `location`/`status` already publish.
- Coordinates are GeoJSON `[lng, lat]`.

## Not yet implemented (planned)
Live-tracking **WebSocket** (`/ws/deliveries/{id}`) — D-4; errand deliveries
(`ref_type: errand`) once the errands module lands; Wompi settlement on delivery
(payments module).
