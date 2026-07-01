# Payments — Frontend & Mobile Contract

> Contract for the **implemented** payment endpoints (source of truth:
> `app/payments`). See `docs/COMMISSION_AND_SUBSCRIPTION.md`.

## Context
Two payment methods (launch): **cash** and **Wompi** (online).
- **Cash:** settled automatically when the delivery is completed — a `Payment`
  (approved) and the ledger entries are written server-side. The frontend does
  nothing special beyond choosing `payment_method: "cash"` on the order.
- **Wompi:** the client requests a payment **intent**, opens Wompi checkout with the
  returned data, and Wompi calls our **webhook** to confirm. On approval the ledger
  is written.

Money is integer **COP**. The platform absorbs Wompi's processing fee.

## Enums
- `method`: `cash` | `wompi`
- `status`: `pending` | `approved` | `declined` | `refunded`

## Model — `PaymentPublic`
```json
{ "id": "665f...", "ref_type": "order", "ref_id": "665e...",
  "payer_id": "665d...", "amount": 10000, "method": "wompi",
  "status": "approved", "created_at": "2026-07-01T12:00:00Z" }
```

## Endpoints

### POST `/api/v1/payments/intent`  (auth — client, Wompi orders)
Create/return a Wompi payment intent for an order the caller owns.
Request: `{ "order_id": "665e..." }`
Response `200` (`IntentResponse`):
```json
{ "payment_id": "665f...", "reference": "BA-…", "amount": 10000,
  "currency": "COP", "public_key": "pub_test_…", "status": "pending" }
```
Open the Wompi checkout widget with `public_key`, `reference`, `amount` (in the
Wompi-expected units), `currency`. Errors: `403 forbidden` (not your order),
`409 not_wompi`, `404 not_found`.

### POST `/api/v1/payments/webhook/wompi`  (Wompi server → us; signed)
Not called by the app. Requires header `X-Event-Signature` (HMAC). Marks the
payment `approved`/`declined` and, on approval, writes the ledger. Idempotent.
Returns `{ "received": true }`. `401` on invalid signature.

### GET `/api/v1/payments/{id}`  (auth — payer or admin)
Returns `PaymentPublic`. Errors: `403 forbidden`, `404 not_found`.

## Client flow (Wompi)
1. Create the order with `payment_method: "wompi"`.
2. `POST /payments/intent` → open Wompi checkout with the returned data.
3. Wompi confirms via the webhook; poll `GET /payments/{id}` until `approved`
   (or move the order forward on your side once approved).

## Notes
- Cash needs no client payment call — it settles on delivery.
- The exact Wompi checkout field mapping / real events-signature scheme is
  finalized at Wompi integration; this contract reflects the current backend.

## Not yet implemented (planned — see COMMISSION_AND_SUBSCRIPTION.md)
Refunds, collaborator/seller **payouts**, periodic **seller settlement** of cash
commissions, and the seller **subscription** billing.
