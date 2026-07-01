# Release process

Versioning and releases are automated with
[**python-semantic-release** (PSR)](https://python-semantic-release.readthedocs.io/),
driven by [Conventional Commits](https://www.conventionalcommits.org/).

## How it works

1. Work lands on `develop` via PRs (`feat:`, `fix:`, `docs:`, `chore:`…).
2. When ready to ship, open a **release PR `develop -> main`** and merge it.
3. On push to `main`, [`.github/workflows/release.yml`](../.github/workflows/release.yml)
   runs PSR, which:
   - reads the commits since the last `vX.Y.Z` tag,
   - computes the next version (config in `pyproject.toml` → `[tool.semantic_release]`),
   - updates `version` in `pyproject.toml` and `CHANGELOG.md`,
   - commits (`chore(release): X.Y.Z [skip ci]`), tags `vX.Y.Z`, and
   - publishes a **GitHub Release** with generated notes.

## Version bump rules

Computed from commit types since the last release:

| Commit | Bump (in 0.x) | Example |
| --- | --- | --- |
| `fix:` | patch | `0.1.0 → 0.1.1` |
| `feat:` | minor | `0.1.0 → 0.2.0` |
| `feat!:` / `BREAKING CHANGE:` | **minor** (not major) | `0.1.0 → 0.2.0` |
| `docs:`, `chore:`, `ci:`, `refactor:`, `test:` | none | — |

We stay in **0.x** on purpose (`allow_zero_version = true`, `major_on_zero = false`):
breaking changes bump the minor until we deliberately cut `1.0.0`. To release 1.0,
bump the version manually once (or flip `major_on_zero = true`).

## One-time setup (required)

`main` is protected (PR required, direct pushes blocked). The release commit that
PSR pushes back to `main` therefore needs a token allowed to bypass that rule.
Pick one:

- **Recommended — PAT secret:** create a fine-grained Personal Access Token (or
  a GitHub App token) with `contents: write` on this repo, from an account that
  is in the branch-protection **bypass list**, and save it as the repo secret
  **`RELEASE_TOKEN`**. The workflow uses it automatically (falls back to
  `GITHUB_TOKEN` if unset).
- **Alternative — ruleset bypass:** add the release actor to the `main` ruleset
  bypass list so the default `GITHUB_TOKEN` push is allowed.

Without one of these, the release job will fail when pushing the version commit.

## Notes

- Conventional Commit hygiene matters: with **squash merges**, the *PR title*
  becomes the commit subject, so keep PR titles conventional (`feat: …`, `fix: …`).
- Dependabot / release / CI chore commits are excluded from the changelog
  (see `exclude_commit_patterns` in `pyproject.toml`).
- No PyPI publish: this is an application, so releases are tag + GitHub Release
  only (no build artifacts).
