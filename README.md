# BarriApp Backend

Backend API for **BarriApp** — a delivery platform for small neighborhood stores
("tiendas de barrio") in Colombia, plus a peer-to-peer errand network
("mandados"). Built with **FastAPI + MongoDB (Beanie) + Redis**.

## Documentation
Design docs live in [`docs/`](docs/README.md) — start with the
[documentation index](docs/README.md). Project overview and locked decisions are
in [`CLAUDE.md`](CLAUDE.md).

## Requirements
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (dependency management)
- MongoDB and Redis (via Docker for local dev — added in F-3)

## Getting started

### Option A — Docker (full stack: API + MongoDB + Redis)
```bash
docker compose up --build
```
Brings up the API with MongoDB and Redis wired in. Then:
- OpenAPI docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/api/v1/health
- Readiness (checks Mongo + Redis): http://localhost:8000/api/v1/health/ready

### Option B — Local (API only; bring your own Mongo/Redis)
```bash
uv sync --extra dev          # install deps
cp .env.example .env         # configure environment
uv run uvicorn app.main:app --reload
```

### Quality gates
```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy app              # type-check
uv run pytest -q             # tests
uv run pre-commit install    # enable pre-commit hooks
```

### Seed data
```bash
uv run python -m scripts.seed
```

## Project layout
```
app/
  core/        # config, (db, security, logging — added in later stories)
  api/         # API routing (v1)
  auth/ users/ stores/ catalog/ orders/ errands/ delivery/
  payments/ notifications/ reviews/ audit/ ai/ admin/   # domain modules
tests/         # pytest suite
docs/          # design documentation
```
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture.
