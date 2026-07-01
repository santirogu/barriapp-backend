# Reviews — Frontend & Mobile Contract

> Contract for the **implemented** review endpoints (source of truth: `app/reviews`).

## Context
After an order is **delivered**, the client can rate the **store** and/or the
**collaborator** (1–5 stars + optional comment). Each rating folds into the
target's denormalized `rating { avg, count }` (shown on stores and collaborator
profiles). One review per target per order.

## Enums
- `target_type`: `store` | `collaborator`

## Model — `ReviewPublic`
```json
{ "id": "665f...", "from_user_id": "665e...", "target_type": "store",
  "target_id": "665d...", "order_id": "665c...", "stars": 5,
  "comment": "Muy bien", "created_at": "2026-07-01T12:00:00Z" }
```

## Endpoints

### POST `/api/v1/reviews`  (auth — client who placed the order)
Rate the store or the collaborator of a **delivered** order. The `target_id` is
derived server-side from the order (its store, or its collaborator).
Request (`ReviewCreate`):
```json
{ "order_id": "665c...", "target_type": "store", "stars": 5, "comment": "Muy bien" }
```
Response `201`: `ReviewPublic`. Errors: `403 forbidden` (not your order),
`409 not_delivered`, `409 no_collaborator` (for `collaborator` when none assigned),
`409 already_reviewed`, `404 not_found`.

### GET `/api/v1/stores/{store_id}/reviews`  (public)
Query `page`/`limit`. A store's reviews, newest first.

## Notes for the client
- Show the rating prompt on the order screen once `status == "delivered"`.
- Store rating appears in `StorePublic.rating`; collaborator rating in
  `CollaboratorProfilePublic.rating`.
- `stars` must be 1–5.

## Not yet implemented (planned)
Listing a collaborator's reviews, editing/deleting a review, and errand-based
reviews (currently reviews are tied to delivered **orders**).
