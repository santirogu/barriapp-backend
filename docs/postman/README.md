# BarriApp — Postman collection

Ready-to-run Postman collection + local environment for the BarriApp API.
Pairs with [../FRONTEND_ONBOARDING.md](../FRONTEND_ONBOARDING.md).

## Files
- `BarriApp.postman_collection.json` — requests grouped by module (Auth, Stores,
  Orders, Delivery, Payments, Errands, AI, Admin, …).
- `BarriApp.local.postman_environment.json` — variables (`base_url`, tokens, ids)
  pointing at `http://localhost:8000/api/v1`.

## Setup
1. Start the backend: `docker compose up --build` (from the repo root).
2. In Postman: **Import** both files. Select the **"BarriApp — Local"** environment
   (top-right).

## Happy path (auto-captures tokens & ids)
1. **Auth → Register**.
2. Copy the OTP printed in the server console into the env var **`otp_code`**.
3. **Auth → Verify OTP** → saves `access_token` + `refresh_token` automatically.
4. **Stores → Create store** (saves `store_id`, grants the seller role) → **Open store**.
5. **Catalog → Create product** (saves `product_id`).
6. **Orders → Create order** (saves `order_id`) → Accept → status preparing → ready.
7. **Delivery / Payments / Reviews / AI** requests reuse the captured ids.

Requests that capture values do so via a test script (`pm.environment.set(...)`),
so later requests "just work".

## Notes
- **Auth**: most requests send `Authorization: Bearer {{access_token}}`.
- **Admin endpoints** (`Admin`, settlement generate, AI knowledge, collaborator
  verification) need a **super_admin** token: there's no API to create one, so
  promote a user to `super_admin` in the DB, log in as them, and paste their
  `access_token` into **`admin_token`**.
- **Wompi webhook** is server-to-server; the `X-Event-Signature` is
  `HMAC-SHA256("reference.transaction_id.status", WOMPI_EVENTS_SECRET)`.
- **WebSocket tracking** (`/ws/deliveries/{id}?token=`) isn't in the collection —
  use a WS client; see [../../app/delivery/FRONTEND.md](../../app/delivery/FRONTEND.md).
- Prefer the live OpenAPI UI at `http://localhost:8000/docs` for exploring schemas.
