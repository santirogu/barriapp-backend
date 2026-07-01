---
name: add-endpoint
description: Add a REST (or WebSocket) endpoint to a BarriApp module following the API contract — RBAC + ownership, Pydantic schemas, standard error shape, audit of state changes, and a traceable test. Use when implementing a new route from docs/API_CONTRACT.md.
---

# Add an endpoint

Implement an endpoint that matches `docs/API_CONTRACT.md`. **Reference:
`app/users/router.py`, `app/auth/router.py`, `app/core/deps.py`, `app/core/errors.py`.**

## Steps
1. **Find the contract row** in `docs/API_CONTRACT.md` (method, path, role, payload).
   Keep the path and role exactly as specified; versioned under `/api/v1`.
2. **Schemas** (`schemas.py`): define request and response Pydantic models. Return
   a public schema, never the raw Document.
3. **Authorization** (`router.py`):
   - Authenticated: inject `user: CurrentUser` (from `app.core.deps`).
   - Role-gated: `Depends(require_roles(Role.SELLER, Role.SUPER_ADMIN))`.
   - Public: no auth dependency.
   - **Ownership** (e.g. a seller editing *their* store) is checked in the
     `service`, raising `AppError(..., status_code=403)` when it fails.
4. **Business logic** in `service.py` (not the router). Raise `AppError` for
   expected failures (`code`, `status_code`); let unexpected errors bubble to the
   global handler.
5. **Audit** every state change:
   ```python
   await audit.record(
       module=AuditModule.<X>, action="<module>.<entity>.<verb>",
       actor_id=user.id, actor_role=primary_role(user),
       target_type="<entity>", target_id=<id>, changes={...},
   )
   ```
   Record failures too where security-relevant (see `app/auth/service.py`).
6. **Errors**: responses use the standard shape `{ "error": { "code", "message", "details"? } }`
   automatically via `AppError` / the registered handlers — don't hand-roll error bodies.
7. **Test — two levels are REQUIRED:**
   - **Unit** (`tests/test_<module>_*.py`, no DB): the endpoint's pure logic
     (query/body parsing, calculations) and each **authorization branch** (e.g.
     non-owner → 403). Extract pure helpers; for authz use duck-typed stand-ins +
     `monkeypatch` of the repository (Beanie docs can't be built without a DB).
     Must pass under `uv run pytest -m "not integration"` (no Docker).
   - **Integration** (`tests/integration/test_<module>.py`, testcontainers):
     success + the main failure via the `api` fixture; assert the audit entry when
     the action is auditable.
   - Tag every test with `@pytest.mark.req("<ID>")`.
8. **Frontend contract**: update `app/<module>/FRONTEND.md` with the new endpoint
   (method, path, auth/role, request/response JSON, error codes) so web & mobile
   stay in sync. Reference: `app/stores/FRONTEND.md`.
9. **Gates**: `uv run ruff check . && uv run ruff format . && uv run mypy app && uv run pytest -q`.

## Checklist
- [ ] Path/role match the contract  - [ ] RBAC + ownership enforced
- [ ] Audit recorded  - [ ] Standard error shape
- [ ] **Unit tests** (pure logic + authz, no Docker) **and** **integration test** green
- [ ] Tests tagged with the backlog ID  - [ ] `FRONTEND.md` updated

## Related skills
`scaffold-module`, `add-model`, `implement-story`.
