---
name: implement-story
description: Implement a full vertical slice for a BarriApp backlog story by its ID (e.g. O-1, S-3, D-2) — model, repository, service, endpoint(s), audit, RBAC, and traceable tests — then run the gates and prepare a conventional commit. Use when picking up a story from docs/MVP_BACKLOG.md.
---

# Implement a backlog story end-to-end

Turn a backlog story into a working, tested vertical slice. **Reference slice:
the users+auth module (`app/users`, `app/auth`, `app/audit`) delivered in PR #1.**

## Inputs
- `story` id (e.g. `O-1`). Optionally a short scope note.

## Steps
1. **Read the story** in `docs/MVP_BACKLOG.md` (the row with that ID) plus the
   relevant flow doc (`ORDER_FLOW.md`, `ERRAND_FLOW.md`, `SELLER_FLOW.md`,
   `COLLABORATOR_ONBOARDING.md`, `ADMIN_PANEL.md`) and `API_CONTRACT.md` /
   `DATA_MODEL.md`. Restate acceptance criteria before coding.
2. **Branch**: from up-to-date `develop`, `git checkout -b feature/<short-slug>`.
3. **Data** — use `add-model` for any new/changed collections; register in
   `app/core/db.py`.
4. **Logic** — repository + service; `AppError` for expected failures; audit every
   state change via `app.audit.service.record(...)`.
5. **API** — use `add-endpoint` for each route the story needs (RBAC + ownership,
   schemas, standard errors); mount routers in `app/api/v1/router.py`.
6. **Tests** — unit (pure logic) + integration (`api` fixture, testcontainers).
   Tag every test with `@pytest.mark.req("<ID>")` for traceability, and assert
   audit entries for auditable actions.
7. **Gates** — all must be green:
   ```bash
   uv run ruff check . && uv run ruff format . && uv run mypy app && uv run pytest -q
   ```
8. **Commit** with Conventional Commits, e.g.
   `feat(orders): create order with totals and commission (O-1)`, ending with the
   `Co-Authored-By` trailer. Push and open a PR **into `develop`** (branches are
   protected: PR + green CI required).

## Definition of done (mirror docs/MVP_BACKLOG.md)
Unit + integration tests green · coverage of the acceptance criteria · audit
events recorded and asserted · RBAC/ownership enforced · gates pass · PR opened
into `develop` and traced to the story ID.

## Related skills
`scaffold-module`, `add-model`, `add-endpoint`.
