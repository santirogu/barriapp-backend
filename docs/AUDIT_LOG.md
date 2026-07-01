# BarriApp — Audit Log (Bitácora)

> Status: **Design**. Cross-cutting requirement. Every meaningful action across
> **all modules** is recorded in an append-only audit log, **readable only by
> `super_admin`**. This document defines the strategy, schema, and coverage.

## 1. Goal

Give the `super_admin` a complete, tamper-evident audit trail of everything that
happens on the platform: who did what, to what, when, from where, and the result.
Covers user lifecycle (creation, login, deactivation, role changes) and every
other module (stores, catalog, orders, errands, deliveries, payments, reviews,
admin/config).

## 2. Principles

- **Append-only / write-once.** Audit entries are never updated or deleted by the
  application. No API exposes update/delete on `audit_logs`.
- **Complete coverage.** Every state-changing action (create/update/delete/status
  change) and every security-relevant event (login success/failure, logout,
  password reset, OTP, token refresh) is logged.
- **Access restricted to `super_admin`.** No other role can read the audit log.
  Reads by the super_admin are themselves audited (`audit.read`).
- **Non-blocking.** Audit writes must not break the main request. Written via a
  reliable async path (queue) with a synchronous fallback for critical security
  events (e.g. login) so nothing is lost.
- **PII-aware.** Store identifiers and diffs, never raw secrets (no passwords,
  tokens, full card data). Sensitive values are redacted/masked.
- **Correlatable.** Each entry carries a `requestId` so related actions can be
  traced across services.

## 3. Data model — `audit_logs`

Extends the collection defined in [DATA_MODEL.md](DATA_MODEL.md) §3.15.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `module` | enum | `auth` \| `users` \| `stores` \| `catalog` \| `orders` \| `errands` \| `delivery` \| `payments` \| `reviews` \| `notifications` \| `ai` \| `admin` |
| `action` | string | Canonical action code (see §4), e.g. `user.login.success` |
| `actorId` | ref→users? | Who performed it (`null` for anonymous/system) |
| `actorRole` | enum? | Role used at the time |
| `targetType` | string? | Affected entity type, e.g. `user`, `order`, `store` |
| `targetId` | ObjectId? | Affected entity id |
| `changes` | object? | `{ before, after }` diff (redacted); omitted for reads |
| `result` | enum | `success` \| `failure` |
| `severity` | enum | `info` \| `warning` \| `critical` |
| `metadata` | object | `{ ip, userAgent, requestId, reason? }` |
| `createdAt` | date | Server timestamp (immutable) |

**Indexes:**
- `{ createdAt: -1 }` — recent-first browsing
- `{ module, action, createdAt: -1 }` — filter by module/action
- `{ actorId, createdAt: -1 }` — "everything user X did"
- `{ targetType, targetId, createdAt: -1 }` — "full history of entity Y"
- `{ result, severity, createdAt: -1 }` — security review of failures

> **Retention:** keep hot in MongoDB for a defined window (e.g. 12–24 months),
> then archive to cold storage (Cloudflare R2). Retention window to be confirmed
> against legal requirements.

## 4. Action catalog (per module)

Canonical `action` codes are `module.entity.verb`. Non-exhaustive baseline:

### auth
`auth.register`, `auth.otp.sent`, `auth.otp.verified`, `auth.otp.failed`,
`auth.login.success`, `auth.login.failed`, `auth.logout`, `auth.token.refresh`,
`auth.password.forgot`, `auth.password.reset`.

### users
`user.created`, `user.updated`, `user.activated`, `user.suspended`,
`user.deleted`, `user.role.granted`, `user.role.revoked`,
`user.address.added`, `user.address.updated`, `user.address.deleted`,
`user.device.registered`.

### stores
`store.created`, `store.updated`, `store.status.changed`, `store.suspended`.

### catalog
`product.created`, `product.updated`, `product.deleted`,
`product.availability.changed`, `category.created`, `category.updated`,
`category.deleted`.

### orders
`order.created`, `order.accepted`, `order.rejected`, `order.status.changed`,
`order.cancelled`, `order.assigned`.

### errands
`errand.created`, `errand.accepted`, `errand.status.changed`,
`errand.cancelled`.

### delivery
`delivery.created`, `delivery.status.changed`, `delivery.proof.uploaded`,
`collaborator.availability.changed`, `collaborator.verification.changed`.

### payments
`payment.intent.created`, `payment.approved`, `payment.declined`,
`payment.refunded`, `payment.webhook.received`, `ledger.entry.created`.

### reviews
`review.created`.

### admin
`admin.metrics.viewed`, `admin.config.updated`, `admin.audit.read`,
`admin.user.status.changed`.

> New actions are added as modules grow; the catalog is the single source of
> truth for `action` values.

## 5. Implementation approach (backend)

- **Central audit service** (`app/audit/`): a single `record(event)` function used
  by all modules. Keeps the schema and redaction rules in one place.
- **Capture mechanisms (combined):**
  1. **Middleware** — captures request-level metadata (`ip`, `userAgent`,
     `requestId`, actor from JWT) and attaches it to the request context.
  2. **Service-layer calls** — business services call `audit.record(...)` at the
     point of the state change, where `before`/`after` and the semantic `action`
     are known (more accurate than inferring from HTTP alone).
  3. **Auth hooks** — login/logout/OTP/token events are recorded explicitly,
     including **failures** (critical for security), written synchronously.
- **Async delivery:** `audit.record` enqueues to Redis/ARQ; a worker persists to
  `audit_logs`. Critical security events also take a synchronous best-effort write.
- **Redaction:** a shared allowlist/denylist ensures passwords, tokens, OTP codes,
  and full payment data never reach the log; only masked identifiers are kept.

## 6. Access (super_admin only)

Exposed under `/api/v1/admin/audit-logs` (see [API_CONTRACT.md](API_CONTRACT.md) §14):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/audit-logs` | List/search: filters `?module=&action=&actorId=&targetType=&targetId=&result=&severity=&from=&to=&q=`, paginated, newest first |
| GET | `/admin/audit-logs/{id}` | Full entry detail (including `changes` diff) |
| GET | `/admin/audit-logs/export` | Export a filtered range (CSV/JSON) for compliance |

- RBAC dependency enforces `super_admin` on every route.
- No `POST`/`PATCH`/`DELETE` — the collection is append-only from the app.
- Every read/export is itself recorded as `admin.audit.read`.

## 7. Relationship to other logging

- **`audit_logs`** = business/security audit trail for the super_admin (this doc).
- **Structured application logs** (Sentry + JSON logs, [ARCHITECTURE.md](ARCHITECTURE.md) §9)
  = operational/debugging telemetry for engineers. Different audience, different
  retention. The two are complementary and must not be conflated.
