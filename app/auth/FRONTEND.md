# Auth — Frontend & Mobile Contract

> Contract for the **implemented** auth endpoints (source of truth: `app/auth`).
> For the broader design see `docs/API_CONTRACT.md` and `docs/ARCHITECTURE.md`.

## Context
Phone-first authentication for Colombia. A user registers with a phone number and
password, verifies a 6-digit OTP sent by SMS, and then logs in to receive JWTs.
The **access token** authorizes API calls; the **refresh token** mints new access
tokens. Identity/roles live in the `users` module.

## Conventions (all modules)
- Base URL: `/api/v1`. JSON in/out. Dates ISO-8601 UTC.
- Auth header: `Authorization: Bearer <accessToken>`.
- Every response carries an `X-Request-ID` header (echo it in bug reports).
- Error shape (all errors): `{ "error": { "code": string, "message": string, "details"?: any } }`.
- Validation errors are `422` with `code: "validation_error"` and `details` = list of field errors.

## Token model
`TokenResponse`:
```json
{ "access_token": "<jwt>", "refresh_token": "<jwt>", "token_type": "bearer" }
```
- Access token is short-lived (default 30 min); refresh token long-lived (default 30 days).
- On `401` with `code: "invalid_token"`, call `POST /auth/refresh`; if that also fails, send the user back to login.

## Endpoints

### POST `/api/v1/auth/register`  (public)
Create an account and trigger an OTP. Does **not** log the user in.
Request:
```json
{ "phone": "+573001112233", "password": "min-8-chars",
  "full_name": "Ana Pérez", "email": "ana@example.com", "accept_habeas_data": true }
```
- `email` optional. `accept_habeas_data` must be `true`.
Response `201`: `{ "message": "Registered. Verify the OTP sent to your phone." }`
Errors: `409 phone_taken`, `409 email_taken`, `422 consent_required`, `422 validation_error`.

### POST `/api/v1/auth/verify-otp`  (public)
Verify the OTP; activates the account and returns tokens.
Request: `{ "phone": "+573001112233", "code": "123456" }` (code = 6 digits)
Response `200`: `TokenResponse`.
Errors: `404 not_found`, `400 invalid_otp` (wrong/expired).

### POST `/api/v1/auth/login`  (public)
Request: `{ "phone": "+573001112233", "password": "..." }`
Response `200`: `TokenResponse`.
Errors: `401 invalid_credentials`, `403 not_verified` (verify OTP first), `403 account_suspended`.

### POST `/api/v1/auth/refresh`  (public)
Request: `{ "refresh_token": "<jwt>" }`
Response `200`: `TokenResponse`.
Errors: `401 invalid_token`, `403 account_suspended`.

### POST `/api/v1/auth/logout`  (auth)
Response `204`. Stateless: the client should discard its tokens.

## Suggested client flow
1. `register` → show "enter the code" screen.
2. `verify-otp` → store tokens securely (Keychain/Keystore).
3. Attach `Authorization` to every request; on `401 invalid_token` → `refresh` → retry once.
4. `logout` → clear stored tokens.

## Not yet implemented (planned — see docs/API_CONTRACT.md §1)
`forgot-password`, `reset-password`. Design them against the docs; this file will
be updated when they ship.
