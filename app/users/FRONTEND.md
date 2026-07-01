# Users — Frontend & Mobile Contract

> Contract for the **implemented** users endpoints (source of truth: `app/users`).

## Context
One identity per person. A user may hold multiple **roles** at once. Role-specific
data lives in other modules (a seller's store in `stores`, etc.). New users start
as `client` with status `pending_verification` until they verify the OTP.

## Enums
- `role`: `client` | `seller` | `collaborator` | `super_admin`
- `status`: `pending_verification` | `active` | `suspended`

## Model — `UserPublic`
```json
{
  "id": "665f...",
  "phone": "+573001112233",
  "email": "ana@example.com",
  "full_name": "Ana Pérez",
  "roles": ["client"],
  "status": "active",
  "avatar_url": null
}
```
`email` and `avatar_url` may be `null`. `roles` grows as the user becomes a seller
(creating a store adds `seller`) or is granted others.

## Endpoints

### GET `/api/v1/me`  (auth)
Returns the current user's `UserPublic`. Use it after login to bootstrap the app
(role-based UI, profile screen). Errors: `401 not_authenticated`.

### PATCH `/api/v1/me`  (auth)
Partial update. Any subset of:
```json
{ "full_name": "New Name", "email": "new@example.com", "avatar_url": "https://..." }
```
Response `200`: updated `UserPublic`. Errors: `401 not_authenticated`, `422 validation_error`.

## Notes for the client
- Drive navigation/permissions from `roles` (e.g. show the "My store" area when
  `roles` includes `seller`).
- `status = suspended` → the API returns `403 account_suspended` on protected
  calls; show a blocked state and route to support.

## Not yet implemented (planned — see docs/API_CONTRACT.md §2)
Address management (`/me/addresses`), device tokens (`/me/device-tokens`),
`become-seller` / `become-collaborator`, and admin user management. (Note: today a
store is created directly via `POST /stores`, which also grants the `seller` role.)
