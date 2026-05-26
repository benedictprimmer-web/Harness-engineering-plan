# Acme Fleet API

## Project

A Python FastAPI service providing the REST and WebSocket API for the Acme Fleet Dashboard. Handles device telemetry ingestion, user authentication, alert rule evaluation, and real-time event streaming. Deployed on AWS ECS; connects to PostgreSQL (primary data), Redis (caching + pubsub), and a TimescaleDB instance (timeseries sensor data).

## Stack

- **Runtime**: Python 3.12, managed with `uv`
- **Framework**: FastAPI 0.111 + Uvicorn
- **Database ORM**: SQLAlchemy 2.0 (async) + Alembic migrations
- **Validation**: Pydantic v2
- **Testing**: pytest + httpx (async test client) + pytest-asyncio
- **Linting**: Ruff (lint + format), mypy (strict)
- **Task queue**: Celery 5 + Redis broker
- **Containerization**: Docker + docker compose (local dev)

## Commands

```bash
uv sync                   # install dependencies from uv.lock
uv run uvicorn src.main:app --reload --port 8000   # dev server
uv run pytest             # run all tests
uv run pytest -x -q       # stop on first failure, quiet output
uv run pytest tests/unit/ # unit tests only
uv run ruff check .       # lint
uv run ruff format .      # format
uv run mypy src/          # type check
uv run alembic upgrade head          # apply pending migrations
uv run alembic revision --autogenerate -m "description"  # create migration
docker compose up -d      # start postgres, redis, timescaledb
docker compose down       # stop services
```

## Architecture

```
src/
  main.py               ← FastAPI app factory, router registration
  config.py             ← Settings (pydantic-settings, reads from env)
  database.py           ← Async SQLAlchemy engine + session factory
  api/
    v1/                 ← API version 1 routes
      devices.py        ← /devices endpoints
      alerts.py         ← /alerts endpoints
      auth.py           ← /auth endpoints (login, refresh, logout)
      ws.py             ← WebSocket endpoint for live data
  models/               ← SQLAlchemy ORM models
  schemas/              ← Pydantic request/response schemas
  services/             ← Business logic (pure functions, no HTTP)
  tasks/                ← Celery task definitions
  middleware/           ← Auth middleware, request logging
tests/
  unit/                 ← Tests for services/ (no DB, mocked deps)
  integration/          ← Tests with real DB (uses pytest fixtures)
  conftest.py           ← Shared fixtures (DB session, test client, factories)
```

## Conventions

- **Async throughout**: all database calls and external API calls use `async/await`
- **Services are pure**: `services/` functions take plain Python objects, return plain objects — no HTTP request/response types, no direct DB sessions (passed as argument)
- **Schemas separate from models**: ORM models in `models/`, Pydantic schemas in `schemas/` — never expose ORM models directly in API responses
- **Settings via config.py**: all configuration comes from `src/config.py` (pydantic-settings) — never `os.environ.get()` directly in application code
- **No print statements**: use `logging` with `structlog` for all output
- **Error handling**: raise `HTTPException` in route handlers; services raise domain exceptions that routes catch and convert

## Environment

Copy `.env.example` to `.env` and fill in:
- `DATABASE_URL` — PostgreSQL connection string (use `postgresql+asyncpg://...` for async)
- `TIMESCALE_URL` — TimescaleDB connection string
- `REDIS_URL` — Redis connection string (default: `redis://localhost:6379/0`)
- `SECRET_KEY` — JWT signing key (generate with `openssl rand -hex 32`)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — optional for local, needed for S3 uploads

Run `docker compose up -d` to start the local Postgres, TimescaleDB, and Redis instances — the `.env.example` default values work against these.

## Gotchas

- **`uv`, not pip**: always use `uv run` or `uv sync`. Don't use `pip install` directly — it bypasses the lockfile.
- **Async SQLAlchemy sessions**: sessions from `database.py` must be used with `async with` and not shared across tasks. Passing a session into a background Celery task will cause errors.
- **Alembic autogenerate misses some things**: array columns, custom types, and TimescaleDB hypertable declarations are not captured by autogenerate. Review generated migrations before applying.
- **pytest-asyncio mode**: the `asyncio_mode = "auto"` setting in `pyproject.toml` means all async test functions run automatically — no need for `@pytest.mark.asyncio`.
- **TimescaleDB vs plain Postgres**: don't run migrations against plain Postgres — the TimescaleDB extension must be installed. Use the Docker image in `docker compose`.
- **Celery tasks in tests**: use `task.apply()` (synchronous) in tests, not `.delay()` — Celery workers aren't running in the test suite.
