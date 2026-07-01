# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# Install dependencies only (no project build → better caching, no README needed).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application code and run from the working directory.
COPY app ./app
ENV PATH="/app/.venv/bin:$PATH"

# Trust the platform's reverse proxy for X-Forwarded-For/Proto (so client IP &
# scheme are correct behind Cloud Run / ECS / ingress). Restrict to the proxy's
# IP/range in stricter setups by overriding FORWARDED_ALLOW_IPS at deploy time.
ENV FORWARDED_ALLOW_IPS=*

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
