# Security & CI Setup Guide — Client Repositories (Admin & Mobile)

This guide replicates the backend's GitHub security and CI/CD hardening in the
**client repositories**:

- **Admin panel** — Next.js + React (e.g. `barriapp-admin`)
- **Mobile / web app** — React Native + Expo (e.g. `barriapp-mobile`)

Both are JavaScript/TypeScript projects, so the tools differ from the Python
backend, but the **structure and policies are identical**: private vulnerability
reporting, Dependabot, Code Scanning (CodeQL + Semgrep SARIF), secret scanning,
and Git Flow branch protection.

> All committed files and docs are in **English** (project convention). Replace
> `OWNER/REPO` and the example repo names with the real ones.

---

## 0. What the backend has (the target state)

| Capability | Backend tool | Where |
| --- | --- | --- |
| Private vulnerability reporting | GitHub setting | Settings → Security |
| Security policy | `SECURITY.md` | repo root |
| Dependency updates + alerts | Dependabot (`uv` ecosystem) | `.github/dependabot.yml` |
| SAST → Code Scanning | Bandit + Semgrep + CodeQL (SARIF) | `.github/workflows/security.yml`, `codeql.yml` |
| Dependency vuln scan (SCA) | `pip-audit` | `security.yml` |
| Secret scanning | GitHub setting + local `gitleaks` | Settings + pre-commit |
| CI gate | ruff + mypy + pytest | `.github/workflows/ci.yml` |
| Branch protection | Ruleset on `main`/`develop` | Settings → Rules |

The sections below give the **JS/TS equivalents**, ready to copy.

---

## 1. GitHub UI toggles (manual — do this once per repo)

These cannot live in a file. In each repo go to **Settings → Code security**
(a.k.a. the *Security and quality* overview) and enable:

- [ ] **Private vulnerability reporting** → *Enable*. Makes the `SECURITY.md`
      "Report a vulnerability" link work.
- [ ] **Dependabot alerts** → *Enable*. Turns on security-driven update PRs
      (independent of the scheduled version updates in `dependabot.yml`).
- [ ] **Dependabot security updates** → *Enable* (auto-PRs for vulnerable deps).
- [ ] **Secret scanning** → *Enable*. Server-side detection of leaked tokens
      (Mapbox, FCM, Wompi public keys, Expo tokens, etc.).
- [ ] **Push protection** (under secret scanning) → *Enable*. Blocks commits that
      contain a secret before they land.

> Free on **public** repositories. On private repos these require GitHub Advanced
> Security (a paid add-on). If a client repo is private and GHAS is not
> available, keep the local `gitleaks` pre-commit hook (Section 6) as the
> fallback and rely on `npm audit` in CI.

`Code scanning` flips from *"Needs setup"* to configured automatically once the
first SARIF is uploaded by the workflows in Section 3.

---

## 2. `SECURITY.md` (repo root)

Same policy as the backend, adjusted for the client repo. Replace `OWNER/REPO`.

```markdown
# Security Policy

## Supported versions

This app is under active development toward its first production release.
Security fixes are applied to the latest `main` (production) and `develop`
(integration) branches only.

| Branch    | Supported          |
| --------- | ------------------ |
| `main`    | :white_check_mark: |
| `develop` | :white_check_mark: |
| others    | :x:                |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately through GitHub's
[private vulnerability reporting](https://github.com/OWNER/REPO/security/advisories/new)
("Report a vulnerability" under the **Security** tab). This keeps the report
confidential until a fix is available.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce (proof of concept if possible).
- Affected screen/component/route and, if known, a suggested fix.

### What to expect

- **Acknowledgement:** within 3 business days.
- **Assessment & triage:** within 7 business days, with a severity estimate.
- **Fix & disclosure:** we aim to ship a fix and publish an advisory as soon as
  practical; we will coordinate a disclosure timeline with you.

## Handling of personal data

BarriApp processes personal data under Colombia's Habeas Data law (Ley 1581).
Client apps must never log or persist raw credentials, JWTs, or PII beyond what
the session requires. Vulnerabilities that expose user data or session tokens
are treated as **critical** and prioritized.

## Scope

In scope: this repository (app code, build/CI config, bundled config).
Out of scope: the BarriApp backend API (report separately) and third-party
services (Wompi, Mapbox, FCM, Expo, Cloudflare) — report those to the vendor.
```

---

## 3. GitHub Actions workflows (`.github/workflows/`)

### 3a. `codeql.yml` — CodeQL for JavaScript/TypeScript

Identical to the backend's, only the language changes (`python` →
`javascript-typescript`).

```yaml
name: CodeQL

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: "30 6 * * 1" # weekly, Mondays 06:30 UTC

concurrency:
  group: codeql-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  analyze:
    name: Analyze JS/TS
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: javascript-typescript
          queries: security-and-quality

      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v4
        with:
          category: "/language:javascript-typescript"
```

### 3b. `security.yml` — Semgrep SARIF + dependency audit

The backend uses Bandit (Python-only) + Semgrep + pip-audit. For JS/TS the SAST
is **Semgrep** with JS/React/TS rule packs, and the SCA is **`npm audit`**
(swap for `pnpm audit` / `yarn npm audit` to match the repo's package manager).

```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "0 6 * * 1" # weekly, Mondays 06:00 UTC

concurrency:
  group: security-${{ github.ref }}
  cancel-in-progress: true

# Required to publish results to Security → Code scanning.
permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  sast-sca:
    name: SAST & dependency scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm" # or "pnpm" / "yarn"

      - name: Install dependencies
        run: npm ci # or: pnpm install --frozen-lockfile / yarn install --immutable

      # --- Semgrep (SAST): SARIF for Code Scanning (reporting) ---
      - name: Semgrep (SARIF)
        run: |
          uvx --from semgrep semgrep scan \
            --config p/javascript --config p/typescript \
            --config p/react --config p/security-audit \
            --sarif --output semgrep.sarif
        continue-on-error: true

      - name: Upload Semgrep SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: semgrep.sarif
          category: semgrep

      # --- Dependency vulnerabilities (SCA, reporting) ---
      - name: npm audit
        run: npm audit --audit-level=high # pnpm audit / yarn npm audit
        continue-on-error: true
```

> `uvx` (from Astral's `uv`) runs Semgrep without a separate install step, mirroring
> the backend. Alternatively use the official `semgrep/semgrep-action` or
> `pip install semgrep`. Keep `continue-on-error: true` for reporting-only, or
> drop it once the team is ready for a **blocking** gate (see Section 7).

### 3c. `ci.yml` — lint, type-check, test gate

The functional CI gate (the required status check for branch protection). Adjust
scripts to the repo's `package.json`.

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build-test:
    name: Lint, type-check & test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type-check
        run: npm run typecheck # e.g. "tsc --noEmit"

      - name: Test
        run: npm test -- --ci
```

---

## 4. `.github/dependabot.yml`

Same shape as the backend, with the **`npm`** ecosystem instead of `uv`. Both
client repos are npm-based (Expo and Next.js). Target `develop` to match Git Flow.

```yaml
# Keeps dependencies patched and opens PRs into `develop`.
# Security updates (from Dependabot alerts) are raised regardless of the schedule.
version: 2
updates:
  # JavaScript / TypeScript dependencies (npm — reads package.json + lockfile).
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "America/Bogota"
    target-branch: "develop"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "chore(deps)"
    groups:
      # Batch minor/patch bumps into one PR to reduce noise; majors stay separate.
      js-minor-patch:
        update-types:
          - "minor"
          - "patch"

  # GitHub Actions used by CI/security workflows.
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "America/Bogota"
    target-branch: "develop"
    commit-message:
      prefix: "chore(ci)"
```

> **Expo note:** the Expo SDK pins many packages to versions compatible with the
> current SDK. Prefer upgrading via `npx expo install --fix` / SDK upgrade rather
> than letting Dependabot bump individual Expo/React Native packages. Consider
> `ignore` entries for `expo`, `react-native`, and `react` majors, and review
> those bumps manually.

---

## 5. Branch protection / rulesets (Git Flow)

Mirror the backend so `main` and `develop` are protected. In **Settings → Rules
→ Rulesets**, create a ruleset targeting `main` and `develop` (or two rulesets):

- [ ] **Require a pull request before merging** (≥ 1 approval recommended).
- [ ] **Require status checks to pass** → select **`Lint, type-check & test`**
      (the `ci.yml` job name). Optionally also require CodeQL.
- [ ] **Require branches to be up to date before merging**.
- [ ] **Block force pushes**.
- [ ] **Restrict deletions**.
- [ ] Allow **admin bypass** only if the team is small (as in the backend).

Workflow: feature branches `feature/*` (or `docs/*`, `ci/*`, `fix/*`) from
`develop` → PR into `develop` → release PR `develop → main`.

---

## 6. Local pre-commit (secret scanning fallback + hygiene)

Mirror the backend's local guardrails so leaks are caught before they reach
GitHub. Add a `.pre-commit-config.yaml` (or Husky + lint-staged if the team
prefers a pure-JS setup):

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
```

Husky alternative (JS-native): `npx husky init` then a `pre-commit` hook running
`npx lint-staged` (ESLint/Prettier) plus `npx gitleaks protect --staged`.

---

## 7. Rollout checklist (per repo)

1. [ ] Add `SECURITY.md`, `.github/dependabot.yml`, `.github/workflows/{ci,security,codeql}.yml`
       on a `ci/security-setup` branch → PR into `develop`.
2. [ ] Ensure `package.json` has `lint`, `typecheck`, and `test` scripts used by `ci.yml`.
3. [ ] Merge, then confirm the workflows run green and a SARIF appears under
       **Security → Code scanning**.
4. [ ] Enable the UI toggles in Section 1.
5. [ ] Create the branch-protection ruleset (Section 5) and set the required
       status check to `Lint, type-check & test`.
6. [ ] Triage the first Dependabot PRs (batch-merge the grouped minor/patch PR;
       review majors — especially Expo/React Native — individually).

---

## 8. Backend ↔ client tool mapping (reference)

| Concern | Backend (Python) | Client (JS/TS) |
| --- | --- | --- |
| Package manager | `uv` | `npm` / `pnpm` / `yarn` |
| SAST | Bandit + Semgrep + CodeQL | Semgrep (`p/javascript`, `p/typescript`, `p/react`) + CodeQL |
| SCA | `pip-audit` | `npm audit` (or `pnpm/yarn audit`) + Dependabot |
| Lint / format | ruff | ESLint + Prettier |
| Type check | mypy | `tsc --noEmit` |
| Tests | pytest | Jest / Vitest / RN Testing Library |
| Secret scan | GitHub + gitleaks | GitHub + gitleaks/Husky |
| Dependabot ecosystem | `uv` | `npm` |
| CodeQL language | `python` | `javascript-typescript` |

The GitHub-side pieces (Dependabot alerts, secret scanning, Code Scanning,
private reporting, rulesets) are **identical** across all three repos — only the
language-specific scanners and package manager differ.
