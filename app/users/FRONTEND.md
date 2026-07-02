# Users — Frontend & Mobile Contract

> Contract for the **implemented** users endpoints (source of truth: `app/users`).

## Context
**One account = one role** (1:1), fixed at registration. Role-specific data lives
in other modules (a seller's store in `stores`, etc.). New users start with status
`pending_verification` until they verify the OTP. A person who wants a second role
registers a separate account.

## Enums
- `role`: `client` | `seller` | `collaborator` | `super_admin` (single value)
- `status`: `pending_verification` | `active` | `suspended`
- `document_type`: `CC` | `CE` | `PA` | `NIT`
- `gender`: `male` | `female` | `other`

## Model — `UserPublic`
```json
{
  "id": "665f...",
  "role": "client",
  "phone": "+573001112233",
  "email": "ana@example.com",
  "first_name": "Ana",
  "last_name": "Pérez",
  "document_type": "CC",
  "document_number": "1032456789",
  "gender": "female",
  "birth_date": "1996-04-12",
  "status": "active",
  "avatar_url": null
}
```
`email`, `avatar_url`, and (for sellers) `gender`/`birth_date` may be `null`.
`document_type`/`document_number` are `null` only on social-login accounts until
the profile is completed.

## Endpoints

### GET `/api/v1/me`  (auth)
Returns the current user's `UserPublic`. Use it after login to bootstrap the app
(role-based UI, profile screen). Errors: `401 not_authenticated`.

### PATCH `/api/v1/me`  (auth)
Partial update. Any subset of:
```json
{ "first_name": "New", "last_name": "Name", "email": "new@example.com", "avatar_url": "https://..." }
```
Response `200`: updated `UserPublic`. Errors: `401 not_authenticated`, `422 validation_error`.

## Notes for the client
- Drive navigation/permissions from the single `role` (e.g. show the "My store"
  area when `role == "seller"`).
- `status = suspended` → the API returns `403 account_suspended` on protected
  calls; show a blocked state and route to support.

## Not yet implemented (planned — see docs/API_CONTRACT.md §2)
Address management (`/me/addresses`), device tokens (`/me/device-tokens`), the
social "complete profile" step, and admin user management. (Note: a seller creates
their store directly via `POST /stores`; the seller role comes from registration.)
