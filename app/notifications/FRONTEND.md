# Notifications — Frontend & Mobile Contract

> Contract for the **implemented** notification endpoints (source of truth:
> `app/notifications`).

## Context
The backend creates an **in-app notification** (and best-effort **push** via FCM)
on key events — e.g. an order being accepted, its status changing, and delivery
milestones. The client lists them, shows an unread badge, marks them read, and
registers its device's FCM token to receive push.

## Enums
- `type`: `order_update` | `errand_update` | `delivery_update` | `system`

## Model — `NotificationPublic`
```json
{ "id": "665f...", "type": "order_update", "title": "Pedido aceptado",
  "body": "La tienda aceptó tu pedido BA-1A2B3C4D.",
  "data": {"order_id": "665e...", "status": "accepted"},
  "read": false, "created_at": "2026-07-01T12:00:00Z" }
```
`data` carries deep-link hints (e.g. `order_id`) for navigation.

## Endpoints

### GET `/api/v1/notifications`  (auth)
Query `page`/`limit`. The caller's notifications, newest first.

### GET `/api/v1/notifications/unread-count`  (auth)
`{ "unread": 3 }` — for the badge.

### POST `/api/v1/notifications/{id}/read`  (auth — owner)
Marks one read. Response `200`: `NotificationPublic`. Errors: `403 forbidden`, `404 not_found`.

### POST `/api/v1/me/device-tokens`  (auth)
Register this device's FCM token (idempotent). Request: `{ "token": "<fcm-token>" }`.
Response `204`. Call on login / token refresh.

## Notes for the client
- Push is **best-effort**: it never blocks the underlying action, and requires a
  registered device token; in-app notifications are always persisted.
- Use `data` to deep-link (e.g. open the order screen from `data.order_id`).
- Notification text is user-facing Spanish.

## Not yet implemented (planned)
Mark-all-read, notification preferences/opt-out, and richer event coverage
(payments, reviews, errands). Real FCM dispatch is a stub in non-production.
