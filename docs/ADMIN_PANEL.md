# BarriApp — Super Admin Panel

> Status: **Design**. Web app (Next.js + React) for the `super_admin`.
> Complements [API_CONTRACT.md](API_CONTRACT.md) (§14, §2, §9),
> [AUDIT_LOG.md](AUDIT_LOG.md), [COLLABORATOR_ONBOARDING.md](COLLABORATOR_ONBOARDING.md),
> and [SELLER_FLOW.md](SELLER_FLOW.md). The super admin has full platform control;
> every action is audited.

## 1. Access & security
- Separate web app; login restricted to users with the `super_admin` role.
- **Elevated protection:** mandatory strong auth (recommend MFA for admins),
  short sessions, IP/audit visibility.
- **Every admin action is audited** (`admin.*`, plus the underlying module action)
  and even **reads of the audit log are logged** (`admin.audit.read`).
- Principle of least surprise: destructive/irreversible actions require explicit
  confirmation and a reason (stored in the audit entry).

## 2. Functional areas

```mermaid
flowchart LR
    D[Dashboard / Metrics] --- U[User management]
    U --- CV[Collaborator verification queue]
    CV --- SM[Store moderation]
    SM --- CAT[Category management]
    CAT --- CFG[Platform config]
    CFG --- DIS[Disputes / moderation]
    DIS --- AUD[Audit log explorer]
```

### 2.1 Dashboard / metrics
- KPIs: orders (by status), **GMV**, active users, active collaborators online,
  new signups, cancellation/rejection rates, errand volume, revenue (platform
  fees). Time filters + trends.
- Source: `GET /admin/metrics` (aggregations; consider a read-optimized rollup
  later if aggregations get heavy).

### 2.2 User management
- Search/list users by role, status, phone/email.
- Suspend/activate (`PATCH /users/{id}/status`), view a user's activity via the
  audit log (`?actorId=`).
- Grant/revoke roles (with reason; audited `user.role.granted/revoked`).

### 2.3 Collaborator verification queue
- Queue of `pending` / `under_review` collaborators (see
  [COLLABORATOR_ONBOARDING.md](COLLABORATOR_ONBOARDING.md)).
- View submitted documents (private signed URLs), approve / reject /
  needs_more_info **with reason** (`PATCH /collaborator/verification`).
- **Manual verification is the MVP mechanism** (decided).

```mermaid
sequenceDiagram
    autonumber
    actor SA as Super Admin
    participant Admin as Admin Web
    participant API
    participant DB

    SA->>Admin: Open verification queue
    Admin->>API: GET pending collaborators
    API-->>Admin: list + document links (signed)
    SA->>Admin: Review docs → decide
    Admin->>API: PATCH /collaborator/verification (approve|reject|needs_more_info + reason)
    API->>DB: update verificationStatus + audit(collaborator.verification.changed)
    API-->>Admin: updated; user notified (FCM)
```

### 2.4 Store moderation
- List/search stores; view detail and reports.
- Suspend/reinstate a store (`PATCH /stores/{id}/status` = suspended), with reason.
- Suspended stores cannot receive orders (see SELLER_FLOW §5).

### 2.5 Category management
- CRUD store/product categories (`/categories`) — shapes discovery/search.

### 2.6 Platform configuration
- Global parameters: **commission model** (being planned separately — see below),
  matching params (radius `R`, offer timeout `T`, retries `N`), errand
  `estimatedCost` cap & tolerance %, delivery fee defaults, feature flags.
- `PATCH /admin/config`; all changes audited (`admin.config.updated`) with before/after.

### 2.7 Disputes / moderation (MVP: manual)
- Review disputes from orders/errands (cost disagreements, no-shows, prohibited
  items), and content/user reports.
- Manual resolution actions (refund flag, warn, suspend), each audited. A formal
  dispute entity can be added when volume justifies it.

### 2.8 Audit log explorer
- Full-text/filtered search over `audit_logs` (module, action, actor, target,
  result, severity, date range) + entry detail with `changes` diff + export.
- **Read-only, super_admin-only, append-only** — see [AUDIT_LOG.md](AUDIT_LOG.md).
- This is the platform's accountability surface: "who did what, to what, when".

## 3. Design notes
- **Reuse the API, don't fork it.** The admin panel consumes the same versioned
  API with `super_admin`-gated endpoints; no separate backend.
- **Read models for heavy views.** Dashboard/metrics may use aggregation
  pipelines now and precomputed rollups later if needed.
- **Confirm + reason on sensitive actions**, captured into the audit trail.

## 4. Endpoints touched
`GET /admin/metrics`, `GET /admin/audit-logs[/{id}|/export]`, `PATCH /admin/config`,
`GET /users`, `PATCH /users/{id}/status`, `PATCH /collaborator/verification`,
`PATCH /stores/{id}/status`, `/categories` CRUD. See [API_CONTRACT.md](API_CONTRACT.md).

## 5. Backlog linkage
Maps to MVP_BACKLOG EPIC 9 (AD-1..AD-4), EPIC 0.5 (audit access LOG-6..8),
D-6 (collaborator verification), and platform config (commissions — pending
planning).
```
