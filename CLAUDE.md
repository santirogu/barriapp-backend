# BarriApp — Backend

Delivery platform for **small neighborhood stores ("tiendas de barrio")** in
**Colombia**, plus a peer-to-peer **errand network ("mandados")** where
collaborators earn money running short favors nearby. Niche underserved by
Rappi/Didi. Mobile-first, with web access.

> **Status: DESIGN / PLANNING phase.** No implementation code yet. This repo
> currently holds design docs only. Do not scaffold code unless asked.

## Roles
One identity (`users`) can hold multiple roles: `super_admin`, `seller` (tendero),
`collaborator` (repartidor/mandadero), `client`.

## Stack (decided)
- **Backend:** Python 3.12 · FastAPI (async) · Beanie ODM · MongoDB Atlas · Redis · ARQ/Celery · WebSockets
- **Clients:** React Native + Expo (mobile + web via react-native-web) — chosen for team's JS/React skills
- **Admin panel:** Next.js + React
- **Payments (Colombia):** Wompi + cash on delivery
- **Maps:** Mapbox · **Push:** FCM · **Storage:** Cloudflare R2 · **Errors:** Sentry
- **AI (phase 2):** RAG with Claude API + MongoDB Atlas Vector Search + tool calling
- **Deploy MVP:** Docker → Railway/Render; **scale:** Cloud Run/ECS Fargate + Terraform
- **CI/CD:** GitHub Actions

## Key decisions & constraints
- Market: **Colombia** (payments, legal, invoicing all CO-specific).
- MVP approach: **balanced** — ship fast but on solid foundations.
- AI assistant: **designed-in from day one**, implemented in phase 2.
- Legal (critical): Habeas Data Ley 1581 + SIC/RNBD registration; DIAN e-invoicing
  for commissions; **collaborator contractor-vs-employee classification is the top
  legal risk** — needs local counsel.
- **Audit trail (P0, cross-cutting):** every meaningful action in every module is
  recorded in an append-only `audit_logs`, **readable only by `super_admin`**
  (login, user creation/deactivation, and every module's state changes). Central
  `audit/` service; no update/delete API. See docs/AUDIT_LOG.md.

## Design docs
- [docs/README.md](docs/README.md) — **documentation index** (start here)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — full architecture (English)
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — MongoDB collections + ER diagram
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — REST/WS endpoints v1
- [docs/MVP_BACKLOG.md](docs/MVP_BACKLOG.md) — epics & prioritized stories
- [docs/ORDER_FLOW.md](docs/ORDER_FLOW.md) — end-to-end order lifecycle (sequence diagrams)
- [docs/AUDIT_LOG.md](docs/AUDIT_LOG.md) — append-only audit trail across all modules (super_admin only)
- [docs/ERRAND_FLOW.md](docs/ERRAND_FLOW.md) — free errand ("mandado") lifecycle, money model, cost reconciliation
- [docs/COLLABORATOR_ONBOARDING.md](docs/COLLABORATOR_ONBOARDING.md) — collaborator KYC/verification & lifecycle
- [docs/SELLER_FLOW.md](docs/SELLER_FLOW.md) — seller store onboarding, catalog & order management, earnings
- [docs/ADMIN_PANEL.md](docs/ADMIN_PANEL.md) — super_admin panel (metrics, moderation, config, audit access)
- [docs/COMMISSION_AND_SUBSCRIPTION.md](docs/COMMISSION_AND_SUBSCRIPTION.md) — revenue model, money flow, settlement, seller subscription
- [docs/REVENUE_PROJECTION.md](docs/REVENUE_PROJECTION.md) — illustrative year-1 revenue projection (adjustable assumptions)
- [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md) — QA/test strategy (shift-left, all test levels, tooling, reporting, traceability)

## Development skills (`.claude/skills/`)
Helper skills that encode the canonical patterns (reference: `app/users` + `app/auth`
+ `app/audit`). Invoke with `/<name>`:
- `scaffold-module` — new domain module (models/schemas/repository/service/router + audit + tests)
- `add-model` — new/extended Beanie model per DATA_MODEL conventions (indexes, geo, partial-unique)
- `add-endpoint` — new route per API_CONTRACT (RBAC + ownership + audit + traceable test)
- `implement-story` — full vertical slice for a backlog ID (e.g. O-1), gates + PR into develop

## Frontend / mobile contracts
Onboarding guide: `docs/FRONTEND_ONBOARDING.md` (start here). Each implemented
module also has a `FRONTEND.md` in its folder documenting the **real**
endpoints/models for web & mobile teams (`app/<module>/FRONTEND.md`).
Keep them in sync with the code as modules evolve.

## Working notes
- The user (Santiago) prefers to plan/refine before implementing.
- Communicate in **Spanish**; all code and docs in English.
- Git Flow: work on `feature/*` from `develop`; PR into `develop` (protected: PR + green CI).
