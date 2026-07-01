# Subscriptions — Frontend & Mobile Contract

> Contract for the **implemented** subscription endpoints (source of truth:
> `app/subscriptions`). See `docs/COMMISSION_AND_SUBSCRIPTION.md` §6.

## Context
Seller **freemium**: the Free plan pays the standard commission; **Premium** pays a
**reduced commission**. Subscribing sets the store's commission override (so orders
immediately bill the reduced rate); cancelling reverts to the global default.
Billing (Wompi recurring) is simulated for now.

## Enums
- `plan`: `free` | `premium`
- `status`: `active` | `past_due` | `cancelled`

## Model — `SubscriptionPublic`
```json
{ "store_id": "665e...", "plan": "premium", "status": "active",
  "commission_rate": 0.05, "price": 30000, "renews_at": "2026-07-31T00:00:00Z" }
```
`price` is COP/month; `commission_rate` is the reduced rate applied while active.
A store with no subscription reports `plan: "free"` (commission_rate null).

## Endpoints (store owner)

### POST `/api/v1/stores/{store_id}/subscription/subscribe`
Activate/renew Premium for the store. Immediately reduces the store's commission.
Response `200`: `SubscriptionPublic`. Errors: `403 forbidden` (not owner), `404 not_found`.

### POST `/api/v1/stores/{store_id}/subscription/cancel`
Cancel the active subscription; the store's commission reverts to the default.
Response `200`: `SubscriptionPublic` (`cancelled`). Errors: `409 no_active_subscription`, `403 forbidden`.

### GET `/api/v1/stores/{store_id}/subscription`
Current subscription; returns a `free` plan if none exists. Response: `SubscriptionPublic`.

## Notes for the client
- After subscribing, new orders for the store bill the reduced commission (reflected
  in `order.amounts.platform_fee`).
- Premium's other perks (priority search, marketing tools, analytics) are planned;
  this ships the commission benefit + lifecycle.

## Not yet implemented (planned — see COMMISSION_AND_SUBSCRIPTION.md)
Real Wompi recurring billing + `past_due` handling/grace period, and the Premium
perks beyond reduced commission (visibility, promos, advanced analytics).
