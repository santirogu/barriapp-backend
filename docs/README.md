# BarriApp — Documentation Index

Delivery platform for **small neighborhood stores ("tiendas de barrio")** in
**Colombia**, plus a peer-to-peer **errand network ("mandados")**. Mobile-first
(React Native + Expo) with web access; Python/FastAPI + MongoDB backend.

> **Status: IMPLEMENTED — MVP + phase-2 AI.** All MVP modules and the AI
> assistant are built and tested; these documents are the design source of truth
> and are kept in sync with the code. See [../CLAUDE.md](../CLAUDE.md) for the
> quick project overview and locked decisions.

## Suggested reading order

1. [ARCHITECTURE.md](ARCHITECTURE.md) — start here: stack, system diagram,
   modules, security, deployment, roadmap, risks.
2. [DATA_MODEL.md](DATA_MODEL.md) — MongoDB collections, ER diagram, indexes,
   state machines.
3. [API_CONTRACT.md](API_CONTRACT.md) — REST/WebSocket endpoints (v1) by module.

## Documents by area

### Foundations
| Doc | What it covers |
|-----|----------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full technical architecture (stack, infra, security, observability, roadmap) |
| [DATA_MODEL.md](DATA_MODEL.md) | Data model: collections, relationships, indexes, ER diagram |
| [API_CONTRACT.md](API_CONTRACT.md) | API contract v1: endpoints, roles, conventions |

### For the frontend / mobile teams
| Doc | What it covers |
|-----|----------------|
| [FRONTEND_ONBOARDING.md](FRONTEND_ONBOARDING.md) | **Start here** — API conventions, auth, core journeys, module map, real-time & AI. Per-module contracts live in `app/<module>/FRONTEND.md`. |
| [CLIENT_SECURITY_SETUP.md](CLIENT_SECURITY_SETUP.md) | Replicate the backend's GitHub security & CI config (Dependabot, CodeQL, Semgrep, secret scanning, branch protection) in the admin (Next.js) and mobile (Expo) repos. |

### Product flows
| Doc | What it covers |
|-----|----------------|
| [ORDER_FLOW.md](ORDER_FLOW.md) | End-to-end store order lifecycle (cash + Wompi), assignment, tracking |
| [ERRAND_FLOW.md](ERRAND_FLOW.md) | Free errand ("mandado") flow, money model, cost reconciliation |
| [SELLER_FLOW.md](SELLER_FLOW.md) | Seller store onboarding, catalog & order management, earnings |
| [COLLABORATOR_ONBOARDING.md](COLLABORATOR_ONBOARDING.md) | Collaborator KYC/verification & lifecycle (manual for MVP) |
| [ADMIN_PANEL.md](ADMIN_PANEL.md) | Super admin panel: metrics, moderation, config, audit access |

### Cross-cutting
| Doc | What it covers |
|-----|----------------|
| [AUDIT_LOG.md](AUDIT_LOG.md) | Append-only audit trail across all modules (super_admin only) |
| [TEST_STRATEGY.md](TEST_STRATEGY.md) | QA strategy: shift-left, all test levels, tooling, reporting, traceability |
| [RELEASE.md](RELEASE.md) | Automated versioning & releases (python-semantic-release, Conventional Commits, `develop → main`) |

### Business
| Doc | What it covers |
|-----|----------------|
| [COMMISSION_AND_SUBSCRIPTION.md](COMMISSION_AND_SUBSCRIPTION.md) | Revenue model, money flow, settlement, seller subscription |
| [REVENUE_PROJECTION.md](REVENUE_PROJECTION.md) | Illustrative revenue projection (commissions + subscriptions) over year 1 |
| [MVP_BACKLOG.md](MVP_BACKLOG.md) | Epics & prioritized user stories |

## Locked decisions (quick reference)
- **Market:** Colombia. **Clients:** React Native + Expo (mobile + web). **Admin:** Next.js.
- **Backend:** FastAPI + Beanie + MongoDB Atlas + Redis; WebSockets for tracking.
- **Payments:** Wompi + cash on delivery. **Maps:** Mapbox. **Push:** FCM. **Storage:** R2.
- **AI assistant:** RAG (Claude API + Atlas Vector Search), designed-in, built in phase 2.
- **Errands:** cash-only at launch. **Collaborator verification:** manual (MVP). No background check at launch.
- **Revenue:** % commission to seller (only stream at launch); delivery 100% to collaborator;
  no client fee; Wompi fee absorbed by platform; cash commission via periodic settlement.
  Seller subscription (freemium) designed, activated post-MVP.
- **Audit:** every action, all modules, append-only, super_admin-only.
- **Docs & code in English; conversation in Spanish.**
