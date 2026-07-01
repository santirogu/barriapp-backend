# Errands — Frontend & Mobile Contract

> Contract for the **implemented** errand endpoints (source of truth: `app/errands`).
> See `docs/ERRAND_FLOW.md`.

## Context
A **free errand ("mandado")** is an open, peer-to-peer favor: a client describes
what they need, offers a fee, and a nearby **approved collaborator** takes it and
completes it. There is no store or catalog. **Cash-only at launch**: on completion
a cash payment settles and the collaborator is credited the `offered_fee`
(errands take no platform commission yet).

## Enums
- `status`: `open` → `assigned` → `in_progress` → `completed`, or `cancelled`.

## Money (integer COP)
- `offered_fee`: what the client pays the collaborator (the collaborator's earning).
- `estimated_cost`: the client's estimate of the purchase to reimburse — informational;
  reimbursement is handled in cash between client and collaborator (cost
  reconciliation is planned, see ERRAND_FLOW.md).

## Model — `ErrandPublic`
```json
{
  "id": "665f...", "code": "MD-1A2B3C4D", "client_id": "665e...",
  "title": "Comprar arroz y aceite", "description": null, "photo_url": null,
  "pickup": null,
  "dropoff": {"label":"Casa","line":"Cra 9","geo":{"type":"Point","coordinates":[-74.081,4.609]}},
  "offered_fee": 8000, "estimated_cost": 20000,
  "status": "open",
  "status_history": [{"status":"open","at":"2026-07-01T12:00:00Z","by":"665e..."}],
  "collaborator_id": null,
  "created_at": "2026-07-01T12:00:00Z"
}
```

## Endpoints

### POST `/api/v1/errands`  (auth — client)
Publish an errand. Request (`ErrandCreate`):
```json
{ "title": "Comprar arroz", "dropoff": {"label":"Casa","line":"Cra 9","geo":{"type":"Point","coordinates":[-74.081,4.609]}},
  "offered_fee": 8000, "description": null, "photo_url": null, "pickup": null, "estimated_cost": 20000 }
```
Response `201`: `ErrandPublic` (status `open`).

### GET `/api/v1/errands`  (auth — client)
Query `page`/`limit`. The caller's errands, newest first.

### GET `/api/v1/errands/available`  (auth — collaborator)
Query `near="lng,lat"` (required), `radius` (m, default 5000). Open errands
nearest-first. Errors: `422 invalid_query`.

### GET `/api/v1/errands/{id}`  (auth — client, assigned collaborator, or admin)
`ErrandPublic`. Errors: `403 forbidden`, `404 not_found`.

### POST `/api/v1/errands/{id}/accept`  (auth — approved collaborator)
Takes an `open` errand → `assigned`. Requires the `collaborator` role.
Errors: `403 forbidden` (not a collaborator), `409 invalid_transition`.

### POST `/api/v1/errands/{id}/status`  (auth — assigned collaborator)
Body `{ "status": "in_progress" | "completed" }`. Only the next step is allowed.
`completed` settles the cash payment + credits the collaborator. Errors:
`403 forbidden`, `409 invalid_transition`.

### POST `/api/v1/errands/{id}/cancel`  (auth — client or admin)
Body `{ "reason": "optional" }`. Allowed while `open` or `assigned`. Response `200`.
Errors: `403 forbidden`, `409 invalid_transition`.

## Notes for the client
- Collaborator flow: browse `available` (with GPS) → `accept` → `in_progress` →
  `completed`. Only users with the `collaborator` role (approved) can accept.
- Coordinates are GeoJSON `[lng, lat]`.

## Not yet implemented (planned — see ERRAND_FLOW.md)
Purchase step + **cost reconciliation** (`/purchase`, `/cost-approval`), prepaid
(Wompi/escrow) errands, live tracking, and disputes.
