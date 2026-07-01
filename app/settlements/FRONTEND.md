# Settlements — Frontend Contract

> Contract for the **implemented** settlement endpoints (source of truth:
> `app/settlements`). See `docs/COMMISSION_AND_SUBSCRIPTION.md` §5.

## Context
For **cash** orders the platform never touches the money, so its commission is a
**receivable from the seller**, recorded as unsettled commission ledger entries.
Periodically the admin generates a **settlement statement** per store (summing
those commissions); the seller pays it and the admin marks it paid. Sellers can
view their own statements.

## Enums
- `status`: `pending` | `paid` | `overdue`

## Model — `SettlementPublic`
```json
{ "id": "665f...", "store_id": "665e...",
  "period_start": "2026-06-01T00:00:00Z", "period_end": "2026-06-15T00:00:00Z",
  "orders_count": 42, "commission_total": 84000,
  "status": "pending", "due_date": "2026-06-20T00:00:00Z", "paid_at": null }
```
`commission_total` is integer COP owed by the seller to the platform.

## Endpoints

### POST `/api/v1/admin/settlements`  (super_admin)
Generate a statement for a store + period. The included cash-commission ledger
entries are marked settled.
Request:
```json
{ "store_id": "665e...", "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-15T00:00:00Z", "due_date": "2026-06-20T00:00:00Z" }
```
Response `201`: `SettlementPublic`.

### GET `/api/v1/admin/settlements`  (super_admin)
Optional `store_id` filter. Returns `SettlementPublic[]` (newest first).

### POST `/api/v1/admin/settlements/{id}/pay`  (super_admin)
Body `{ "payment_ref": "nequi-123" }` (optional). Marks it `paid` (idempotent).
Response: `SettlementPublic`.

### GET `/api/v1/settlements`  (auth — seller)
The caller's stores' settlements, newest first.

## Notes
- Wompi (prepaid) commissions are already settled at payment time and are **not**
  part of these statements — only cash commissions are.
- Amounts are integer COP.

## Not yet implemented (planned)
Automatic periodic generation (scheduled job), overdue detection + auto-suspend,
and seller-facing payment of the statement via Wompi.
