# BarriApp — Test Strategy & QA Plan

> Status: **Design**. Authored from an SDET perspective covering functional and
> non-functional quality, shift-left, and black/white-box testing. Aligns with
> the stack in [ARCHITECTURE.md](ARCHITECTURE.md) (FastAPI backend, React
> Native/Expo clients, Next.js admin) and traces to [MVP_BACKLOG.md](MVP_BACKLOG.md).

## 1. Objectives & principles

- **Shift-left.** Quality starts at design and code time, not at the end. Static
  analysis, unit and contract tests run on every commit/PR; expensive suites
  (E2E, load) run later in the pipeline and on schedules.
- **Test pyramid.** Many fast unit tests, fewer component/integration, fewer
  contract/API, few UI/E2E. Non-functional suites (security, performance) run
  as gated stages, not on every commit.
- **Black-box + white-box, deliberately.**
  - *White-box* (structure-aware): unit, component, code coverage, mutation.
  - *Black-box* (behavior-only): API/contract, UI/E2E, exploratory, load, DAST.
- **Everything traceable.** Every test maps to a backlog ID (e.g. `A-2`, `O-1`,
  `LOG-6`) via tags, feeding a Requirements Traceability Matrix (RTM).
- **Visible results.** Every execution produces a report aggregated into a
  historical dashboard with trends, flaky detection, and failure triage.
- **Quality gates.** PRs cannot merge unless gates pass (coverage threshold, no
  new criticals in SAST, contract compatibility, lint).

### Definition of Done (per story)
Unit + component tests written and green · API/contract tests for new endpoints ·
coverage gate met · SAST/deps clean · audit events asserted (for auditable
actions) · E2E updated if user-facing · report published & traced to backlog ID.

## 2. Test levels & types

### 2.1 Unit tests (white-box)
- **Scope:** pure functions, services, validators, pricing/commission logic,
  state-machine transitions, permission checks — isolated with mocks/fakes.
- **Backend stack:** `pytest`, `pytest-asyncio`, `pytest-cov` (+ `coverage.py`),
  `hypothesis` (property-based, e.g. money/total calculations), `factory-boy` +
  `faker` (test data), `freezegun` (time), `pytest-mock`.
- **Frontend stack:** `Jest` + `React Native Testing Library` (mobile),
  `Vitest`/`Jest` + `React Testing Library` (Next.js admin), `msw` (mock API).
- **Targets:** ≥ 80% line coverage on core domain modules; branch coverage on
  state machines and money math. Mutation testing (`mutmut` for Python,
  `Stryker` for JS) on the highest-risk modules (payments, orders, audit).

### 2.2 Component tests (white/grey-box)
- **Backend:** a module + its real dependencies (DB, cache) but external services
  faked. Run against an **ephemeral MongoDB & Redis** via
  `testcontainers-python` (Docker) or `mongomock` for lighter cases. Validates
  repositories, indexes, geo queries, and audit writes end-to-end within a module.
- **Frontend:** rendered components/screens with mocked navigation & API
  (`msw`), plus **Storybook** with interaction tests for visual/behavioral states
  and design-system regression.

### 2.3 Contract tests (black-box, consumer-driven + schema)
- **Consumer-driven:** **Pact** between each client (mobile, admin) and the API —
  prevents breaking changes; Pact Broker stores contracts and verifies
  provider/consumer compatibility as a gate.
- **Schema/spec-driven:** **Schemathesis** generates property-based tests from the
  FastAPI **OpenAPI** schema (fuzzes inputs, checks responses conform).
  **Spectral** lints the OpenAPI spec itself in CI.
- **Why both:** Pact guards real consumer expectations; Schemathesis guards the
  full API surface against the published contract.

### 2.4 API / integration tests (black-box)
- **Scope:** endpoints end-to-end through the app against ephemeral Mongo/Redis:
  auth flows, RBAC/ownership, order lifecycle, payments (Wompi sandbox +
  webhook signature), idempotency, pagination, error shapes, and **audit-log
  assertions** for every auditable action.
- **Stack:** `pytest` + `httpx.AsyncClient` (in-process), `Tavern` (YAML-driven
  cases) optional, `respx` to stub outbound HTTP (Wompi/FCM/SMS), **Newman**
  (Postman collections) for a portable smoke suite runnable by non-devs.
- **WebSocket:** tests for `/ws/deliveries/{id}` (subscribe, receive location,
  auth enforcement).

### 2.5 UI / E2E tests (black-box)
- **Mobile (RN/Expo):** **Maestro** (primary — simple YAML flows, fast, great for
  smoke/critical paths) with **Detox** as an option for deeper gray-box native
  cases. Run on Android emulator + iOS simulator in CI, and on real devices via a
  device cloud (**BrowserStack** / **Sauce Labs**) for coverage across OS versions.
- **Web (Next.js admin):** **Playwright** (multi-browser, traces, video, network
  mocking).
- **Scope:** critical journeys only — register/login, browse stores, place order
  (cash + Wompi sandbox), live tracking, collaborator accept/deliver, admin views
  audit log. E2E is intentionally thin (top of the pyramid).

### 2.6 Security tests (non-functional, black + white-box)
Aligned with **OWASP ASVS**, **OWASP API Security Top 10**, and **OWASP MASVS**
(mobile). See also [AUDIT_LOG.md](AUDIT_LOG.md) and ARCHITECTURE §6.
- **SAST:** `Semgrep` (custom + community rules), `Bandit` (Python), `ESLint
  security` plugins (JS/TS).
- **Dependency / SCA:** `pip-audit` + `Safety` (Python), `npm audit` /
  `osv-scanner` (JS), **Snyk** or GitHub **Dependabot** for continuous alerts.
- **Secret scanning:** `gitleaks` / `trufflehog` in CI + pre-commit.
- **DAST:** **OWASP ZAP** (baseline + API scan against staging using the OpenAPI
  spec) on a schedule.
- **Container/IaC:** `Trivy` (image + Terraform misconfig), `Checkov` (IaC).
- **Targeted tests:** authZ/ownership bypass, JWT handling, rate-limit
  enforcement, Wompi webhook signature spoofing, PII redaction in logs/audit,
  IDOR on `/orders`,`/stores`,`/admin/audit-logs`. Periodic manual pentest before
  major releases.

### 2.7 Performance / load / stress tests (non-functional, black-box)
- **Tooling:** **k6** (primary — scriptable in JS, native Grafana output, HTTP +
  **WebSocket** support) with **Locust** (Python) as an alternative the team can
  extend easily.
- **Profiles:**
  - *Load:* expected peak concurrency (e.g. lunch/dinner order surges).
  - *Stress:* ramp beyond capacity to find the breaking point.
  - *Spike:* sudden surge (promotion) and recovery.
  - *Soak/endurance:* sustained load for hours → memory leaks, connection pools.
- **Critical scenarios:** store geo-search (`/stores?near=`), order creation +
  stock decrement (write contention), collaborator matching, and **live-tracking
  WebSocket fan-out** (many subscribers per delivery).
- **SLOs to assert:** p95 latency per key endpoint, error rate < X%, throughput,
  and DB/Redis saturation thresholds. Results dashboards in **Grafana** (k6 →
  Prometheus/InfluxDB or Grafana Cloud).

### 2.8 Accessibility & usability (non-functional)
- Automated a11y checks: `axe-core` (Playwright integration) for web; RN
  accessibility props asserted in component tests. Manual usability passes on
  critical flows given the barrio audience (low-friction, cash-first UX).

## 3. Technology stack summary

| Level / type | Primary tools | Notes / alternatives |
|--------------|---------------|----------------------|
| Unit (backend) | pytest, pytest-asyncio, pytest-cov, hypothesis, factory-boy, faker, freezegun | mutmut (mutation) |
| Unit (frontend) | Jest / Vitest, RTL / RN Testing Library, msw | Stryker (mutation) |
| Component | testcontainers-python, mongomock, Storybook | — |
| Contract | Pact (+ Pact Broker), Schemathesis, Spectral | — |
| API / integration | pytest + httpx, respx, Tavern, Newman | — |
| UI/E2E mobile | Maestro | Detox; BrowserStack/Sauce device cloud |
| UI/E2E web | Playwright | axe-core for a11y |
| Security | Semgrep, Bandit, pip-audit/Safety, gitleaks, OWASP ZAP, Trivy, Checkov | Snyk, Dependabot |
| Performance | k6 | Locust; Gatling |
| Coverage/quality | coverage.py, SonarCloud/SonarQube | Codecov |
| Reporting | Allure, ReportPortal | see §5 |
| Test management / RTM | Xray or Zephyr (Jira) / TestRail | ReportPortal for exec history |

## 4. Traceability

- **Test IDs & tags.** Every test is tagged with its backlog ID(s), e.g.
  `@pytest.mark.req("A-2","LOG-3")`, Playwright `test.info().annotations`,
  Maestro flow tags. A CI step compiles a **Requirements Traceability Matrix
  (RTM)** mapping backlog stories → tests → last execution → status.
- **Coverage of requirements.** RTM surfaces stories with no tests (gaps) and
  tests with no requirement (orphans).
- **Execution traceability.** Each run is stamped with commit SHA, branch, PR,
  environment, and build number; **ReportPortal** keeps full execution history,
  trends, and flaky-test detection. Optional **Xray/Zephyr** links executions to
  Jira issues for audit-grade traceability.
- **Correlation with product audit.** API/integration tests assert that auditable
  actions produce the expected `audit_logs` entries (ties QA to the audit
  requirement).

## 5. Reporting & visibility

- **Per-run rich reports:** **Allure** aggregates pytest, Playwright, Maestro,
  and Newman results into one HTML report (steps, attachments, screenshots,
  videos, logs), published as a CI artifact / GitHub Pages per build.
- **Historical dashboard & triage:** **ReportPortal** — trends over time, flaky
  detection, AI-assisted failure clustering, and requirement/tag filtering. This
  is the "single pane of glass" for stakeholders.
- **Code quality gate:** **SonarCloud** — coverage import, duplication, code
  smells, and a subset of SAST, enforcing a **quality gate** on PRs.
- **Performance dashboards:** **Grafana** (k6 metrics via Prometheus/InfluxDB) —
  latency percentiles, throughput, error rates per scenario, comparable across
  runs.
- **Security findings:** SARIF uploaded to **GitHub Code Scanning** (Semgrep/ZAP/
  Trivy) for a centralized, tracked view; Dependabot/Snyk alerts on dependencies.
- **Notifications:** CI posts run summaries + report links to Slack/email on
  failure and on scheduled non-functional runs.

## 6. CI/CD integration & quality gates (shift-left)

Pipeline stages (GitHub Actions), fastest-first:

1. **pre-commit (local):** ruff/eslint format+lint, gitleaks, unit-test-changed.
2. **On PR:** lint → unit → component → contract (Pact verify + Schemathesis +
   Spectral) → API/integration → SAST (Semgrep/Bandit) → SCA (pip-audit/npm
   audit) → coverage & Sonar quality gate. **All must pass to merge.**
3. **On merge to main / staging deploy:** full API suite → E2E (Playwright +
   Maestro on emulators) → DAST (ZAP baseline) → publish Allure + push to
   ReportPortal.
4. **Scheduled (nightly/weekly):** performance (k6 load/soak), full device-cloud
   E2E matrix, deep ZAP scan, dependency re-scan.
5. **Pre-release:** stress/spike tests, manual exploratory + security review,
   RTM sign-off.

## 7. Test data & environments

- **Environments:** `local` (docker-compose) → `test/CI` (ephemeral containers) →
  `staging` (production-like, isolated Atlas/Redis) → `production` (smoke only).
- **Data management:** factories (`factory-boy`/`faker`) generate deterministic
  data; seed scripts for reference data; **each test isolates its data** (fresh
  DB per suite via testcontainers) — no shared mutable state.
- **Secrets/sandboxes:** Wompi **sandbox**, FCM test project, mock SMS provider;
  no real PII in non-prod. Synthetic Colombian data (phones, addresses, geo).
- **Flakiness policy:** quarantine + auto-retry-once with tracking; flaky tests
  are ticketed, not ignored.

## 8. Metrics & KPIs

- Coverage (line/branch) + mutation score on critical modules.
- Requirement coverage % (from RTM) and gap count.
- Pass rate, flaky rate, mean time to detect/triage.
- Escaped defects (found in prod vs. pre-prod).
- Performance SLO adherence (p95 latency, error rate) per release.
- Security: open findings by severity, mean time to remediate, dependency freshness.

## 9. Rollout plan (phased, alongside the build)

| Phase | Focus |
|-------|-------|
| 0 — Foundations | Wire pytest/Jest, coverage, ruff/eslint, pre-commit, CI skeleton, Allure. Establish DoD & gates. |
| 1 — Core MVP | Unit + component + API/contract for auth, users, stores, orders, payments, **audit**; SAST/SCA gates; Playwright/Maestro smoke of critical journeys; ReportPortal + Sonar live. |
| 2 — Non-functional | k6 load/soak on hot paths + WebSocket; OWASP ZAP DAST; device-cloud E2E matrix; a11y checks; RTM formalized. |
| 3 — Hardening | Mutation testing on payments/orders/audit; stress/spike; pre-release exploratory + pentest; SLO dashboards. |

## 10. Ownership

- **Whole team owns quality** (shift-left). SDET/QA owns the strategy, frameworks,
  gates, RTM, and reporting infrastructure; developers write unit/component/API
  tests with their features; security tooling is automated in CI with periodic
  specialist review.
