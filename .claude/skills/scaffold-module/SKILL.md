---
name: scaffold-module
description: Scaffold a new BarriApp backend domain module (models/schemas/repository/service/router) following the canonical layout, with audit wiring, router registration, and a test skeleton. Use when starting a new module such as stores, catalog, orders, errands, delivery, payments, reviews, notifications, ai, or admin.
---

# Scaffold a domain module

Create a new module under `app/<module>/` that matches the project's canonical
pattern. The **reference implementation is `app/users/` + `app/auth/` + `app/audit/`** —
mirror their structure and conventions.

## Inputs
- `module` name (e.g. `stores`). Must match a package already stubbed under `app/`.

## Steps
1. **Read the references** before writing anything:
   - `app/users/{models,schemas,repository,service,router}.py`
   - `app/audit/service.py` (how state changes are audited)
   - `app/core/deps.py` (RBAC), `app/core/errors.py` (AppError)
   - `docs/ARCHITECTURE.md` §4 (module layout), `docs/DATA_MODEL.md`, `docs/API_CONTRACT.md`.
2. **Create the files** in `app/<module>/` (only those the module needs):
   - `models.py` — Beanie `Document`(s) + enums (`StrEnum`) + embedded `BaseModel`s.
     Use `add-model` conventions (indexes, `_utcnow`, geo 2dsphere, partial-unique).
   - `schemas.py` — Pydantic request/response models (never expose the raw Document;
     add a `from_<entity>` classmethod like `UserPublic.from_user`).
   - `repository.py` — Beanie query functions (`get_by_id`, `find_one`, `insert`, …).
   - `service.py` — business logic; raises `AppError` for expected failures; calls
     `app.audit.service.record(...)` for every state change.
   - `router.py` — `APIRouter(tags=["<module>"])`; endpoints use `CurrentUser` /
     `require_roles(...)` and enforce ownership in the service.
3. **Register documents**: add the new `Document`(s) to `_document_models()` in
   `app/core/db.py`.
4. **Mount the router**: include it in `app/api/v1/router.py` with the correct prefix
   per `docs/API_CONTRACT.md`.
5. **Tests — two levels are REQUIRED** (keep the pyramid; see the shared
   "Testing" section below):
   - **Unit** (`tests/test_<module>_*.py`, no DB): pure logic + authorization
     branches. Extract pure helpers so they don't need a DB.
   - **Integration** (`tests/integration/test_<module>.py`, testcontainers):
     the DB-backed happy path + a key failure, via the `api` fixture.
   - Tag every test with `@pytest.mark.req("<ID>")`.
6. **Run the gates** and fix everything until green:
   ```bash
   uv run ruff check . && uv run ruff format . && uv run mypy app && uv run pytest -q
   ```

## Conventions (do not deviate)
- English for all code, comments, and docs.
- Async everywhere; type-annotate fully (mypy strict).
- Every auditable action → `audit.record(module=AuditModule.<X>, action="<module>.<entity>.<verb>", …)`.
- Money in COP as integers/Decimal per the model; geo coordinates `[lng, lat]`.
- Keep the layered split (router → service → repository); no DB queries in routers.

## Testing (two levels — required for every module)
The pyramid is mandatory: **many fast unit tests + a few integration tests.**
- **Unit (no DB, must run without Docker):** cover pure logic (parsing, criteria
  building, calculations) and **authorization branches**. Beanie documents CANNOT
  be instantiated without `init_beanie` (`CollectionWasNotInitialized`), so:
  extract pure helpers to plain functions, and for authz tests use duck-typed
  stand-ins (`types.SimpleNamespace`) plus a mocked repository (`monkeypatch`).
  Verify: `uv run pytest -m "not integration"` passes with no Docker.
- **Integration (`@pytest.mark.integration`, testcontainers):** the DB-backed
  happy path + a key failure, asserting audit entries for auditable actions.
- Reference: `tests/test_stores_unit.py`, `tests/test_service_unit.py`,
  `tests/integration/test_stores.py`.

## Related skills
`add-model`, `add-endpoint`, `implement-story`.
