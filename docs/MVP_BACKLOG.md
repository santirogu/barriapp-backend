# BarriApp — MVP Backlog

> Status: **Design**. Priority: `P0` (must-have to launch), `P1` (important),
> `P2` (nice-to-have / phase 2). Approach: **balanced** — a functional MVP on
> solid foundations. Relative estimates in *points* (Fibonacci).

## How to read it
Each epic groups user stories in the form *"As a [role] I want [action] so that
[value]"* with summarized acceptance criteria. The order reflects a suggested
build sequence.

---

## EPIC 0 — Technical foundations (P0)
*The base everything is built on. Not user-visible but blocking.*

| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| F-1 | Set up FastAPI project + modular structure + per-environment config | P0 | 3 |
| F-2 | MongoDB Atlas connection + Beanie + initial migration/seed | P0 | 3 |
| F-3 | Docker + local docker-compose (API, Mongo, Redis) | P0 | 3 |
| F-4 | CI/CD with GitHub Actions (lint → test → build → deploy staging) | P0 | 5 |
| F-5 | Error handling, structured logging, Sentry | P0 | 3 |
| F-6 | Test baseline (pytest + ephemeral Mongo) + ruff + pre-commit | P0 | 3 |

---

## EPIC 0.5 — Audit trail / bitácora (P0, cross-cutting)
*Every meaningful action in every module is recorded, append-only, readable only
by `super_admin`. Built early because all other modules must emit audit events.
Full design in [AUDIT_LOG.md](AUDIT_LOG.md).*

| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| LOG-1 | As the system I want a central append-only audit service used by all modules | P0 | 5 |
| LOG-2 | As the system I want request middleware to capture actor, IP, user-agent, requestId | P0 | 3 |
| LOG-3 | As the system I want auth events logged (login success/failure, logout, OTP, reset) | P0 | 3 |
| LOG-4 | As the system I want user-lifecycle events logged (create, activate, suspend, role change) | P0 | 3 |
| LOG-5 | As the system I want each module to emit its state-change events (stores, catalog, orders, errands, delivery, payments, reviews, admin) | P0 | 5 |
| LOG-6 | As a super_admin I want to search/filter the audit log (by module, action, actor, target, result, date) | P0 | 5 |
| LOG-7 | As a super_admin I want to export a filtered range for compliance | P1 | 3 |
| LOG-8 | As the system I want audit reads by the super_admin to themselves be audited | P0 | 2 |

**Key criteria:** append-only (no update/delete API); async write with sync fallback
for critical security events; redaction of secrets/PII; super_admin-only access.

---

## EPIC 1 — Authentication and roles (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| A-1 | As a user I want to register with my phone so I can create my account | P0 | 5 |
| A-2 | As a user I want to verify my phone via OTP (SMS) | P0 | 5 |
| A-3 | As a user I want to log in and refresh my session (JWT access+refresh) | P0 | 5 |
| A-4 | As a user I want to accept the Habeas Data consent at registration | P0 | 2 |
| A-5 | As the system I want RBAC by role + ownership on every endpoint | P0 | 5 |
| A-6 | As a client I want to recover my password | P1 | 3 |

**Key criteria:** rotating tokens, rate limiting on `/auth`, versioned and auditable consent.

---

## EPIC 2 — User profile and addresses (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| U-1 | As a user I want to view/edit my profile | P0 | 2 |
| U-2 | As a client I want to manage my addresses with a map location | P0 | 5 |
| U-3 | As a user I want to register my device to receive notifications | P0 | 2 |
| U-4 | As a client I want to become a seller (create a store) | P0 | 3 |
| U-5 | As a client I want to apply as a collaborator (stays pending) | P0 | 3 |

---

## EPIC 3 — Stores and catalog (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| S-1 | As a seller I want to create/edit my store (data, logo, location) | P0 | 5 |
| S-2 | As a seller I want to set schedule and delivery config (radius, fee, minimum) | P0 | 3 |
| S-3 | As a seller I want to manage products (create/edit/price/stock/availability) | P0 | 5 |
| S-4 | As a client I want to see stores near me (geospatial search) | P0 | 5 |
| S-5 | As a client I want to see a store's catalog | P0 | 3 |
| S-6 | As a client I want to search products/stores by name and category | P1 | 3 |

**Key criteria:** 2dsphere index on stores; image upload to R2.

---

## EPIC 4 — Orders (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| O-1 | As a client I want to build a cart and create an order (with totals + fee + commission) | P0 | 8 |
| O-2 | As a seller I want to receive and accept/reject orders | P0 | 5 |
| O-3 | As a seller I want to advance the status (preparing → ready) | P0 | 3 |
| O-4 | As a client/seller I want to cancel an order based on its status | P0 | 3 |
| O-5 | As a client I want to see the history and detail of my orders | P0 | 3 |
| O-6 | As the system I want to store an items snapshot + status history | P0 | 3 |

---

## EPIC 5 — Assignment and delivery/tracking (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| D-1 | As a seller/system I want to assign a nearby collaborator to the order | P0 | 8 |
| D-2 | As a collaborator I want to go online/offline and see my jobs | P0 | 5 |
| D-3 | As a collaborator I want to update my location during delivery | P0 | 5 |
| D-4 | As a client I want to see the delivery live (WebSocket) | P0 | 8 |
| D-5 | As a collaborator I want to record proof of delivery (photo) | P1 | 3 |
| D-6 | As a super_admin I want to verify/approve collaborator documents | P0 | 3 |

**Key criteria:** WebSocket + Redis Pub/Sub; location throttling; 2dsphere on collaborators.

---

## EPIC 6 — Payments (P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| P-1 | As a client I want to pay cash on delivery | P0 | 3 |
| P-2 | As a client I want to pay with Wompi (PSE/card/Nequi) | P0 | 8 |
| P-3 | As the system I want to process the Wompi webhook (signature + states) | P0 | 5 |
| P-4 | As the system I want to record commissions and earnings in the ledger | P0 | 5 |
| P-5 | As a collaborator/seller I want to see my balance and movements | P1 | 3 |
| P-6 | As the system I want to compute the seller % commission on order creation (per-store rate override + global default) | P0 | 3 |
| P-7 | As the platform I want periodic seller settlement statements for cash-order commissions | P1 | 5 |

**Commission model:** percentage to seller (only revenue stream at launch),
delivery fee 100% to collaborator, no client fee, Wompi fee absorbed by platform,
cash commission collected via periodic settlement. See
[COMMISSION_AND_SUBSCRIPTION.md](COMMISSION_AND_SUBSCRIPTION.md).

---

## EPIC 7 — Notifications (P0/P1)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| N-1 | As a user I want to receive push notifications for my order's status changes | P0 | 5 |
| N-2 | As a user I want to see my in-app notifications | P1 | 3 |

---

## EPIC 8 — Reviews (P1)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| R-1 | As a client I want to rate the store and collaborator after delivery | P1 | 3 |
| R-2 | As a client I want to see a store's reviews | P1 | 2 |

---

## EPIC 9 — Super Admin panel (P0/P1)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| AD-1 | As a super_admin I want to see key metrics (orders, GMV, users) | P1 | 5 |
| AD-2 | As a super_admin I want to manage users (suspend/activate) | P0 | 3 |
| AD-3 | As a super_admin I want to configure global commissions | P1 | 3 |
| AD-4 | Audit log access → see EPIC 0.5 (LOG-6/7/8) | P0 | — |

---

## EPIC 10 — Free errands (P1 → early phase 2)
*Key product differentiator. Can launch shortly after the core.*

| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| E-1 | As a client I want to post an errand (title, destination, offered fee, photo) | P1 | 5 |
| E-2 | As a collaborator I want to see open errands near me | P1 | 5 |
| E-3 | As a collaborator I want to accept and execute an errand | P1 | 5 |
| E-4 | As a client I want to track and pay for my errand | P1 | 5 |

---

## EPIC 11 — AI assistant (P2 — phase 2)
*Contemplated in the design; the data model is already prepared (`ai_knowledge`).*

| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| AI-1 | Knowledge ingestion (FAQs, policies, catalog) with embeddings into Atlas Vector | P2 | 8 |
| AI-2 | As a user I want to ask the assistant specific questions (RAG) | P2 | 8 |
| AI-3 | As the assistant I want to query the real API (order status, stores) via tool calling | P2 | 8 |
| AI-4 | Per-user conversation history | P2 | 3 |

---

## EPIC 12 — Seller subscription / freemium (P2 — post-MVP)
*Designed now (see [COMMISSION_AND_SUBSCRIPTION.md](COMMISSION_AND_SUBSCRIPTION.md)),
activated after the MVP. Premium's hook = reduced commission + visibility + marketing.*

| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| SUB-1 | Subscription data model + effective-commission resolution (free vs premium) | P2 | 5 |
| SUB-2 | As a seller I want to subscribe to Premium (recurring billing via Wompi) | P2 | 8 |
| SUB-3 | Premium benefits: reduced commission, priority search, faster settlement | P2 | 8 |
| SUB-4 | Premium marketing tools (promotions, coupons, push to nearby clients) | P2 | 8 |
| SUB-5 | Premium advanced analytics | P2 | 5 |

---

## Legal / compliance (cross-cutting, P0)
| ID | Story | Priority | Pts |
|----|-------|----------|-----|
| L-1 | Privacy policy + Terms per role (with legal counsel) | P0 | — |
| L-2 | Database registration with the SIC (RNBD) | P0 | — |
| L-3 | Collaborator Terms (contractor model) reviewed legally | P0 | — |
| L-4 | DIAN electronic invoicing for commissions | P1 | — |

---

## Definition of "ready to launch MVP" (P0 complete)
Auth + roles · profile/addresses · store + catalog + geo search · full order flow ·
assignment + live tracking · cash + Wompi payment · status push · minimal admin ·
**full audit trail (bitácora) across all modules, super_admin-only** ·
P0 legal resolved.

**Out of the initial MVP:** free errands (EPIC 10) and AI assistant (EPIC 11) →
first phase-2 deliverables, already contemplated in architecture and data.
