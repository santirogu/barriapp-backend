# BarriApp — API Contract (v1)

> Status: **Design**. Base: FastAPI. Prefix: `/api/v1`. Format: JSON.
> Auth: `Authorization: Bearer <accessToken>` (JWT). Live docs via OpenAPI (`/docs`).
> Roles: `super_admin`, `seller`, `collaborator`, `client`, `public` (no auth).

## Conventions

- **Pagination:** `?page=1&limit=20` → response `{ items, page, limit, total }`.
- **Errors:** `{ error: { code, message, details? } }` with an appropriate HTTP status.
- **Dates:** ISO-8601 UTC.
- **Idempotency:** payment creation endpoints accept an `Idempotency-Key` header.
- **Versioning:** breaking changes → `/api/v2`.

---

## 1. Auth (`/auth`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | public | Register choosing one `role` (seller/client/collaborator) + role-specific fields (see auth/FRONTEND.md); 18+ for client/collaborator |
| POST | `/auth/verify-otp` | public | Verify OTP code sent via SMS |
| POST | `/auth/login` | public | Login → `{ accessToken, refreshToken }` |
| POST | `/auth/refresh` | public | Refresh access token |
| POST | `/auth/logout` | auth | Invalidate refresh token / device token |
| POST | `/auth/forgot-password` | public | Start recovery |
| POST | `/auth/reset-password` | public | Confirm new password |

## 2. Users & profiles (`/users`, `/me`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/me` | auth | Own profile (includes the account's single `role`) |
| PATCH | `/me` | auth | Update basic data |
| POST | `/me/complete-profile` | auth | Social sign-up only: set document/birth date/gender (18+) → activate |
| GET | `/me/addresses` | auth | List addresses |
| POST | `/me/addresses` | auth | Add address (with geo) |
| PATCH | `/me/addresses/{id}` | auth | Edit / mark default |
| DELETE | `/me/addresses/{id}` | auth | Delete |
| POST | `/me/device-tokens` | auth | Register FCM token |
| POST | `/me/become-seller` | client | Create store profile (request seller role) |
| POST | `/me/become-collaborator` | client | Create collaborator profile (stays `pending`) |
| GET | `/users` | super_admin | List/search users |
| PATCH | `/users/{id}/status` | super_admin | Suspend/activate |

## 3. Stores (`/stores`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/stores` | public | List stores; filters `?near=lng,lat&radius=&category=&q=` |
| GET | `/stores/{id}` | public | Store detail |
| GET | `/stores/{id}/products` | public | Store catalog |
| POST | `/stores` | seller | Create store (or via become-seller) |
| PATCH | `/stores/{id}` | seller/owner | Edit data, schedule, delivery config |
| PATCH | `/stores/{id}/status` | seller/owner, super_admin | Open/close/suspend |
| GET | `/stores/{id}/orders` | seller/owner | Store orders (filter by status) |

## 4. Products (`/stores/{id}/products`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/stores/{id}/products` | seller/owner | Create product |
| PATCH | `/products/{id}` | seller/owner | Edit (price, stock, availability) |
| DELETE | `/products/{id}` | seller/owner | Delete/hide |
| GET | `/products/{id}` | public | Detail |

## 5. Categories (`/categories`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/categories` | public | List (store/product) |
| POST/PATCH/DELETE | `/categories/...` | super_admin | Administration |

## 6. Orders (`/orders`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/orders` | client | Create order (compute totals, fee, commission) |
| GET | `/orders` | client | My orders |
| GET | `/orders/{id}` | client/owner/collaborator | Detail |
| POST | `/orders/{id}/cancel` | client, seller/owner | Cancel (based on status) |
| POST | `/orders/{id}/accept` | seller/owner | Store accepts |
| POST | `/orders/{id}/status` | seller/owner | Advance `preparing`→`ready` |
| POST | `/orders/{id}/assign` | seller/owner, super_admin | Assign collaborator (or auto-match) |

## 7. Errands / Mandados (`/errands`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/errands` | client | Post an errand (title, dropoff, offered fee) |
| GET | `/errands` | client | My errands |
| GET | `/errands/available` | collaborator | Open errands nearby `?near=lng,lat&radius=` |
| POST | `/errands/{id}/accept` | collaborator | Take the errand |
| POST | `/errands/{id}/status` | collaborator | Advance `in_progress`→`completed` |
| POST | `/errands/{id}/cancel` | client | Cancel (if still `open`) |

## 8. Deliveries & tracking (`/deliveries`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/deliveries/{id}` | involved parties | Current status and route |
| POST | `/deliveries/{id}/location` | collaborator | Update location (throttled) |
| POST | `/deliveries/{id}/proof` | collaborator | Upload proof of delivery |
| WS | `/ws/deliveries/{id}` | involved parties | **WebSocket** — live location/status |

## 9. Collaborator (`/collaborator`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/collaborator/availability` | collaborator | online/offline |
| GET | `/collaborator/jobs` | collaborator | Assigned deliveries + errands |
| GET | `/collaborator/earnings` | collaborator | Balance and movements (ledger) |
| PATCH | `/collaborator/verification` | super_admin | Approve/reject documents |

## 10. Payments (`/payments`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/payments/intent` | client | Create payment intent (Wompi) → checkout data |
| POST | `/payments/webhook/wompi` | public (signed) | Wompi confirmation webhook |
| GET | `/payments/{id}` | involved parties | Payment status |

## 11. Reviews (`/reviews`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/reviews` | client | Rate store/collaborator after delivery |
| GET | `/stores/{id}/reviews` | public | Store reviews |

## 12. Notifications (`/notifications`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/notifications` | auth | List |
| POST | `/notifications/{id}/read` | auth | Mark read |

## 13. AI Assistant (`/ai`) — phase 2
| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/ai/chat` | auth | Message to the assistant (RAG + tool calling into our own API) |
| GET | `/ai/conversations/{id}` | auth | History |

## 14. Admin (`/admin`) — super_admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/metrics` | KPIs (orders, GMV, active users) |
| GET | `/admin/audit-logs` | Search audit trail: `?module=&action=&actorId=&targetType=&targetId=&result=&severity=&from=&to=&q=`, paginated, newest first |
| GET | `/admin/audit-logs/{id}` | Full audit entry detail (incl. `changes` diff) |
| GET | `/admin/audit-logs/export` | Export filtered range (CSV/JSON) for compliance |
| PATCH | `/admin/config` | Global commissions, platform parameters |

> **Audit log is append-only and super_admin-only.** No create/update/delete
> endpoints exist for `audit_logs`; the app writes entries internally. Every read
> and export is itself audited (`admin.audit.read`). See [AUDIT_LOG.md](AUDIT_LOG.md).

---

## Security notes
- RBAC on every endpoint (FastAPI dependency validating role + ownership).
- Rate limiting on `/auth/*` and `/ai/chat`.
- Wompi webhook validates HMAC signature.
- PII never in logs; audit trail for `super_admin` actions.
