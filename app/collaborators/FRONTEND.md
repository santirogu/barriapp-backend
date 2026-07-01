# Collaborators — Frontend & Mobile Contract

> Contract for the **implemented** collaborator endpoints (source of truth:
> `app/collaborators`). See `docs/COLLABORATOR_ONBOARDING.md`.

## Context
A collaborator (courier / errand-runner) is a user who applies, submits KYC data,
is **manually verified by an admin** (MVP), and then can go **online** (sharing a
GPS location) to be matched to deliveries/errands. The `collaborator` role is
granted **on approval**, not on application.

## Enums
- `vehicle_type`: `walk` | `bike` | `motorcycle` | `car`
- `verification_status`: `pending` | `under_review` | `needs_more_info` | `approved` | `rejected`
- `availability`: `offline` | `online` | `on_delivery` (`on_delivery` is system-managed)

## Model — `CollaboratorProfilePublic`
```json
{
  "id": "665f...", "user_id": "665e...",
  "vehicle_type": "bike",
  "documents": { "id_number": "1032456789", "license_url": null },
  "verification_status": "pending",
  "availability": "offline",
  "rating": { "avg": 0.0, "count": 0 },
  "balance": 0
}
```
`balance` is integer COP (pending payout).

## Endpoints

### POST `/api/v1/me/become-collaborator`  (auth)
Apply to become a collaborator. Request:
```json
{ "vehicle_type": "bike", "id_number": "1032456789", "license_url": null }
```
Response `201`: `CollaboratorProfilePublic` (status `pending`).
Errors: `409 already_collaborator`.
> For motorized vehicles the frontend should also collect license/SOAT; upload
> images to storage and pass URLs (fuller document flow is planned).

### GET `/api/v1/collaborator/me`  (auth)
Returns the caller's `CollaboratorProfilePublic`. Errors: `404 not_found` (no profile).

### POST `/api/v1/collaborator/availability`  (auth — approved collaborator)
Go online (with GPS) or offline. Request:
```json
{ "status": "online", "lng": -74.081, "lat": 4.609 }
```
- `online` requires `lng` + `lat`; `offline` needs neither.
Response `200`: `CollaboratorProfilePublic`.
Errors: `403 not_approved`, `422 location_required`, `422 invalid_status`, `404 not_found`.

### PATCH `/api/v1/collaborator/{user_id}/verification`  (super_admin)
Approve / reject / request more info. Request:
```json
{ "status": "approved", "reason": null }
```
- On `approved`, the user is granted the `collaborator` role.
Response `200`: `CollaboratorProfilePublic`. Errors: `403 forbidden`, `404 not_found`.

## Notes for the client
- Onboarding UX: apply → show "under review" until an admin approves → then enable
  the "Go online" toggle. Poll `GET /collaborator/me` (or refresh on resume).
- While `online`, send periodic location updates during a delivery (that endpoint
  arrives with the `delivery` module).

## Not yet implemented (next: `delivery` module)
Assignment to orders, delivery status/location updates, proof of delivery, live
tracking (WebSocket), and `GET /collaborator/jobs`. See `docs/API_CONTRACT.md`
§8/§9 and `docs/ORDER_FLOW.md`.
