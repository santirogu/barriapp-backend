# Security Policy

## Supported versions

BarriApp is under active development toward its first production release.
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
[private vulnerability reporting](https://github.com/santirogu/barriapp-backend/security/advisories/new)
("Report a vulnerability" under the **Security** tab). This keeps the report
confidential until a fix is available.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce (proof of concept if possible).
- Affected component/endpoint and, if known, a suggested fix.

### What to expect

- **Acknowledgement:** within 3 business days.
- **Assessment & triage:** within 7 business days, with a severity estimate.
- **Fix & disclosure:** we aim to ship a fix and publish an advisory as soon as
  practical; we will coordinate a disclosure timeline with you.

## Handling of personal data

BarriApp processes personal data under Colombia's Habeas Data law (Ley 1581).
Vulnerabilities that expose user data (clients, sellers, collaborators) or the
`super_admin`-only audit trail are treated as **critical** and prioritized.

## Scope

In scope: this backend repository (API, auth, data access, CI/CD config).
Out of scope: third-party services we integrate with (Wompi, Mapbox, FCM,
Cloudflare R2, MongoDB Atlas) — report those to the respective vendors.
