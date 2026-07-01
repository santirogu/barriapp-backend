# BarriApp Backend — Frontend & Mobile Onboarding

Executive summary + practical guide for the web (Next.js/React) and mobile
(React Native/Expo) teams building against the BarriApp API. For the exact,
authoritative contract of each area, open the linked per-module `FRONTEND.md`.

---

## 1. What BarriApp is
A delivery platform for **small neighborhood stores ("tiendas de barrio")** in
Colombia, plus a peer-to-peer **errand network ("mandados")**. Four roles on one
identity (a user can hold several):
- **client** — browses stores, orders, posts errands, chats with the assistant.
- **seller** — owns a store, manages catalog & orders (granted when creating a store).
- **collaborator** — courier/errand-runner (granted on admin approval).
- **super_admin** — metrics, moderation, config, audit (web admin panel).

## 2. Tech & conventions (read once)
- **Base URL:** `/api/v1`. JSON in/out. Dates are ISO-8601 UTC.
- **Auth:** `Authorization: Bearer <accessToken>` (JWT). See §4.
- **Errors — always this shape:**
  ```json
  { "error": { "code": "invalid_credentials", "message": "…", "details": null } }
  ```
  Switch on `error.code` (stable), show `message` (may be Spanish, user-facing).
  Validation errors: `422` with `code: "validation_error"` and `details` = field errors.
- **Pagination:** `?page=1&limit=20` on list endpoints (limits capped, e.g. 100).
- **IDs** are Mongo ObjectId strings.
- **Money** is **integer COP** (e.g. `3500` = $3.500). Format on the client.
- **Geo** is GeoJSON `[longitude, latitude]` (NOT lat,lng).
- Every response has an **`X-Request-ID`** header — include it in bug reports.
- Interactive API docs (OpenAPI/Swagger): **`GET /docs`** on a running server.

## 3. Run the backend locally
```bash
docker compose up --build      # API + MongoDB + Redis
# → http://localhost:8000/docs  (try endpoints live)
# → http://localhost:8000/api/v1/health
```
No cloud accounts needed for dev: payments (Wompi) and the AI LLM (Claude) run with
**safe local fallbacks** unless keys are configured, so the whole API is usable
offline. OTPs and pushes are logged to the server console in dev.

## 4. Authentication flow (implement first) — [app/auth/FRONTEND.md](../app/auth/FRONTEND.md)
Phone-first, OTP-verified.
1. `POST /auth/register` `{ phone, password, full_name, email?, accept_habeas_data: true }` → `201`.
2. `POST /auth/verify-otp` `{ phone, code }` → **`{ access_token, refresh_token, token_type }`** (in dev the code is printed to the server log).
3. `POST /auth/login` `{ phone, password }` → tokens. `POST /auth/refresh` `{ refresh_token }` → new tokens.
4. Attach `Authorization: Bearer <access>` to every call. On `401 invalid_token` → call `refresh` → retry once → else send to login.
5. `POST /me/device-tokens` `{ token }` — register the FCM token for push (see notifications).

**Client tips:** store tokens securely (Keychain/Keystore); drive UI from
`GET /me`.roles; a `403 account_suspended` means a blocked account.

## 5. Modules & where to find each contract
| Area | Endpoints (high level) | Contract |
|------|------------------------|----------|
| Auth | register / verify-otp / login / refresh / logout | [auth](../app/auth/FRONTEND.md) |
| Users | `GET/PATCH /me`, roles/status | [users](../app/users/FRONTEND.md) |
| Stores | create (become-seller), **geo search**, get, update, status | [stores](../app/stores/FRONTEND.md) |
| Catalog | categories, per-store products CRUD, availability | [catalog](../app/catalog/FRONTEND.md) |
| Orders | create (totals+commission), accept/status/cancel, list/get | [orders](../app/orders/FRONTEND.md) |
| Collaborators | become-collaborator, verification (admin), availability | [collaborators](../app/collaborators/FRONTEND.md) |
| Delivery | assign, status/location/proof, jobs, **tracking WS** | [delivery](../app/delivery/FRONTEND.md) |
| Payments | Wompi intent + webhook, cash settle, get | [payments](../app/payments/FRONTEND.md) |
| Errands | publish, browse-nearby, accept, status, cancel | [errands](../app/errands/FRONTEND.md) |
| Reviews | rate store/collaborator after delivery | [reviews](../app/reviews/FRONTEND.md) |
| Notifications | list, unread-count, read, device-tokens | [notifications](../app/notifications/FRONTEND.md) |
| Settlements | seller statements (admin) + seller view | [settlements](../app/settlements/FRONTEND.md) |
| Subscriptions | seller Premium (reduces commission) | [subscriptions](../app/subscriptions/FRONTEND.md) |
| Admin | metrics, user moderation, audit explorer, config | [admin](../app/admin/FRONTEND.md) |
| AI assistant | knowledge (admin), chat (RAG + tools), conversations | [ai](../app/ai/FRONTEND.md) |

## 6. Core user journeys (call sequences)

### Client — place & track an order
1. `GET /stores?near=lng,lat&radius=&q=` → pick a store.
2. `GET /stores/{id}/products?available_only=true` → build a cart.
3. `POST /orders` `{ store_id, items:[{product_id, qty}], delivery_address, payment_method }`
   → returns `amounts` (items, delivery_fee, **platform_fee**, total). Render server totals.
4. If `payment_method: "wompi"` → `POST /payments/intent` → open Wompi checkout.
5. Track: open **`WS /api/v1/ws/deliveries/{deliveryId}?token=…`** (snapshot + live updates),
   or poll `GET /orders/{id}`. Status: `pending→accepted→preparing→ready→assigned→picked_up→delivered`.
6. After `delivered`: `POST /reviews` `{ order_id, target_type: "store"|"collaborator", stars, comment }`.

### Seller — run a store
`POST /stores` (become seller) → `PATCH /stores/{id}/status "open"` → manage products
(`POST /stores/{id}/products`, `PATCH /products/{id}`) → receive orders
(`GET /stores/{id}/orders`), `POST /orders/{id}/accept` → `/status` `preparing`→`ready`
→ `POST /orders/{id}/assign` (nearest collaborator). Optional: `POST /stores/{id}/subscription/subscribe` (Premium → lower commission).

### Collaborator — deliver
`POST /me/become-collaborator` → (admin approves) → `POST /collaborator/availability`
`{ status:"online", lng, lat }` → get assigned → drive delivery via
`POST /deliveries/{id}/status` (`en_route_pickup→picked_up→en_route_dropoff→delivered`),
`POST /deliveries/{id}/location` (throttled), `POST /deliveries/{id}/proof`.

### Errands ("mandados")
Client `POST /errands` `{ title, dropoff, offered_fee, … }`; collaborator
`GET /errands/available?near=lng,lat` → `POST /errands/{id}/accept` → `/status`
`in_progress`→`completed` (cash settles on completion).

## 7. Real-time tracking (WebSocket)
`WS /api/v1/ws/deliveries/{id}?token=<accessToken>` (token in query — browsers can't
set WS headers). Sends a snapshot then live `{ delivery_id, status, route }` updates.
Closes `4401` (bad token) / `4403` (not your delivery). Fallback: poll `GET /deliveries/{id}`.

## 8. AI assistant — [app/ai/FRONTEND.md](../app/ai/FRONTEND.md)
`POST /ai/chat` `{ message, conversation_id?, order_id? }` → grounded answer +
`sources` + `tools_used`. It can **call backend tools itself** (e.g. answer
"¿dónde está mi pedido?" by fetching the caller's latest order — no `order_id` needed).
Keep `conversation_id` for a threaded chat.

## 9. Suggested client architecture
- **Token layer:** secure storage + an HTTP interceptor that adds the bearer,
  refreshes on `401 invalid_token`, and retries once.
- **Role-driven navigation:** read `roles` from `GET /me` to reveal client/seller/
  collaborator areas.
- **Money & dates:** format integer COP and ISO timestamps in the UI layer.
- **Optimistic vs. authoritative:** always render server-provided `amounts`/statuses.
- **Type safety:** generate a client from the OpenAPI schema (`/openapi.json`) if useful.

## 10. What's stubbed in dev (so you can build now)
- **Wompi**: `intent` returns checkout data; approval is via a signed webhook. Cash
  orders settle automatically on delivery.
- **OTP/SMS & push (FCM)**: logged server-side in dev (no real gateway needed).
- **AI LLM**: deterministic grounded fallback unless `ANTHROPIC_API_KEY` is set.
- **Geo search & vector search**: work on local Mongo; Atlas Vector Search is the
  production path for AI retrieval.

## 11. Not yet available (roadmap)
Wompi recurring billing & refunds/payouts, audit export, response streaming for the
assistant, errand cost reconciliation, and additional Premium perks. Check each
module's `FRONTEND.md` "Not yet implemented" section for specifics.
