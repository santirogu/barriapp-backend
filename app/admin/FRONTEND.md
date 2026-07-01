# Admin — Frontend Contract (Super Admin panel)

> Contract for the **implemented** admin endpoints (source of truth: `app/admin`).
> All endpoints require the **`super_admin`** role. See `docs/ADMIN_PANEL.md`.
> Consumed by the Next.js admin panel (not the mobile app).

## Auth
Every route needs `Authorization: Bearer <accessToken>` for a `super_admin`.
Non-admins get `403 forbidden`. All admin actions (and audit-log reads) are audited.

## Endpoints

### GET `/api/v1/admin/metrics`
Platform KPIs:
```json
{ "users": 120, "stores": 15, "open_stores": 9, "active_collaborators": 4,
  "orders_total": 320, "orders_delivered": 280, "errands_total": 40,
  "gmv": 8500000, "platform_revenue": 850000 }
```
`gmv` = COP total of delivered orders; `platform_revenue` = sum of commission ledger.

### GET `/api/v1/admin/users`
Query `role`, `user_status`, `q` (phone/email substring), `page`, `limit`.
Returns `UserPublic[]` (see `app/users/FRONTEND.md`).

### PATCH `/api/v1/admin/users/{user_id}/status`
Body `{ "status": "active" | "suspended" | "pending_verification" }`. A suspended
user is blocked (`403 account_suspended`) on protected calls. Response: `UserPublic`.

### GET `/api/v1/admin/audit-logs`
Search the append-only audit trail. Query `module`, `action`, `actor_id`,
`result`, `page`, `limit` (default 50, max 200). Returns `AuditLogPublic[]`
(newest first):
```json
{ "id":"...", "module":"orders", "action":"order.created", "actor_id":"...",
  "actor_role":"client", "target_type":"order", "target_id":"...",
  "result":"success", "severity":"info", "changes":{...}, "meta":{"request_id":"..."},
  "created_at":"..." }
```

### GET `/api/v1/admin/audit-logs/{id}`
Full `AuditLogPublic`. Errors: `404 not_found`.

### GET `/api/v1/admin/config` / PATCH `/api/v1/admin/config`
Platform configuration (singleton):
```json
{ "default_commission_rate": 0.10, "settlement_frequency_days": 15, "updated_at": "..." }
```
PATCH accepts any subset. Response: updated config.

## Notes for the admin frontend
- Audit log is **read-only + append-only**; there is no create/update/delete.
- The audit explorer is the accountability surface — filter by `module`/`action`/`actor_id`.
- Every audit-log read is itself recorded as `admin.audit.read`.

## Not yet implemented (planned — see ADMIN_PANEL.md)
Audit export (CSV/JSON), store moderation shortcuts (use `PATCH /stores/{id}/status`),
dispute resolution, rollup/precomputed metrics, and wiring `admin/config` into live
commission resolution.
