# Industrial Asset Management Platform

An enterprise-grade, async Python backend for managing industrial assets — robots, machines, devices, factories, and more.

Built with **aiohttp** + **asyncpg** + **PostgreSQL**, the platform is designed around real-world engineering concerns: configuration layering, async DB pools, structured logging, middleware, database migrations, and background workers.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Database Migrations](#database-migrations)
- [Background Tasks](#background-tasks)
- [Middleware](#middleware)
- [Documentation](#documentation)

---

## Project Overview

AssetOps is a web platform that centralises management of industrial assets across sites and facilities. Phase 1 delivers a monolithic async backend providing REST APIs consumed by a React frontend.

**Domain entities (planned across phases):**

| Entity | Description |
|---|---|
| Assets | Machines, robots, and devices |
| Sites & Factories | Physical locations |
| Maintenance Logs | Scheduled and ad-hoc service records |
| Alerts | Threshold breaches and fault notifications |
| Users & Roles | Access control |
| Telemetry | Real-time sensor data |
| Audit History | Change trail across all entities |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    aiohttp App                      │
│                                                     │
│  ┌──────────────┐   ┌────────────┐  ┌────────────┐  │
│  │  Middleware  │   │  Handlers  │  │  Services  │  │
│  │  request-id  │   │  (routes)  │  │ (business  │  │
│  │  error hdlr  │   │            │  │   logic)   │  │
│  │  req logger  │   └─────┬──────┘  └─────┬──────┘  │
│  └──────────────┘         │               │         │
│                           └───────┬───────┘         │
│                                   │                 │
│                        ┌──────────▼──────────┐      │
│                        │    Repositories     │      │
│                        │  (raw asyncpg SQL)  │      │
│                        └──────────┬──────────┘      │
│                                   │                 │
│               ┌───────────────────┼───────────────┐ │
│               │  Background Tasks          │    │ │
│               │  config_refresher_task     │    │ │
│               │  env_watcher (base)        │    │ │
│               │  env_local_watcher (local) │    │ │
│               └───────────────────────────┘    │ │
└───────────────────────────────────────────────────┘─┘
                            │
                   ┌────────▼────────┐
                   │   PostgreSQL 16 │
                   │  (via Docker)   │
                   └─────────────────┘
```

---

## Technology Stack

### Backend
| Package | Version | Purpose |
|---|---|---|
| `aiohttp` | ≥ 3.13.5 | Async HTTP server & routing |
| `asyncpg` | ≥ 0.31.0 | Async PostgreSQL driver |
| `pydantic` | ≥ 2.13.4 | Data validation and modelling |
| `pydantic-settings` | ≥ 2.14.1 | Typed env/settings management |
| `alembic` | ≥ 1.18.4 | Database schema migrations |
| `sqlalchemy` | ≥ 2.0.49 | Alembic migration metadata |
| `python-dotenv` | ≥ 1.2.2 | `.env` file loading |

### Infrastructure
| Tool | Purpose |
|---|---|
| PostgreSQL 16 | Primary relational database |
| Docker / docker-compose | Local development environment |
| Nginx *(planned)* | Reverse proxy |

### Frontend *(planned)*
| Tool | Purpose |
|---|---|
| React + Vite | Dashboard UI |

### Runtime
- **Python ≥ 3.14**
- **uv** for package management

---

## Project Structure

```
.
├── .env                          # Base environment variables (never commit secrets)
├── .env.local                    # Local overrides — highest priority, not committed
├── docker-compose.yml            # Postgres container for local dev
├── pyproject.toml                # Project metadata and dependencies
├── alembic.ini                   # Alembic migration config
│
├── migrations/
│   └── versions/
│       ├── 58937b0f928d_create_assets_table.py
│       └── 6a5c1b09f820_create_app_config_table.py
│
├── app/
│   ├── main.py                   # App factory, startup/cleanup lifecycle
│   │
│   ├── core/
│   │   ├── logging.py            # Structured logging setup
│   │   └── config/
│   │       ├── config.py         # Settings model (pydantic-settings)
│   │       ├── config_manager.py # Runtime config merging (env + DB)
│   │       └── config_background_tasks.py  # watch_file_task, sync_base_env, sync_local_env, DB refresher
│   │
│   ├── db/
│   │   └── postgres.py           # asyncpg connection pool factory
│   │
│   ├── models/
│   │   └── asset.py              # Pydantic domain models
│   │
│   ├── repositories/
│   │   ├── asset_repository.py   # SQL for assets table
│   │   └── config_repository.py  # SQL for app_config table
│   │
│   ├── services/
│   │   └── asset_services.py     # Business logic layer
│   │
│   ├── api/
│   │   ├── handlers/             # aiohttp request handlers
│   │   └── routes/               # Route registration
│   │
│   └── middleware/
│       ├── request_id.py         # Injects X-Request-ID header
│       ├── request_logger.py     # Logs method, path, status, duration
│       └── error_middleware.py   # Centralised exception → JSON response
│
└── docs/
    └── config-env-db-sync.md     # Env → DB config sync deep-dive
```

---

## Getting Started

### Prerequisites

- Docker & docker-compose
- Python ≥ 3.14
- `uv` package manager

### 1. Start the database

```bash
docker-compose up -d
```

This starts a PostgreSQL 16 container named `assetops-postgres` on port `5432`.

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

Copy or edit `.env` at the project root:

```env
APP_NAME=AssetOps
APP_HOST=0.0.0.0
APP_PORT=8080

DB_HOST=localhost
DB_PORT=5432
DB_NAME=assetops
DB_USER=postgres
DB_PASSWORD=postgres
```

Optionally create `.env.local` for local overrides (highest priority, not committed to git):

```env
APP_NAME=Local-override
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

### 5. Start the application

```bash
uv run python -m app.main
```

The server will be available at `http://localhost:8080`.

### Health check

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

---

## Configuration

Configuration is layered across three sources, applied in priority order:

| Layer | Source | Priority |
|---|---|---|
| Database | `app_config` table | Lowest (base) |
| Base env file | `.env` → read by `pydantic-settings` | Medium |
| Local env file | `.env.local` → read by `pydantic-settings` | Highest (overrides all) |

On startup the application:
1. Reads settings from both `.env` and `.env.local` into a typed `Settings` object (`.env.local` wins on conflict).
2. Upserts `.env` values into the `app_config` table (skips unchanged values).
3. Merges DB rows with local settings into an in-memory `runtime_config` (local settings win).

Two background file watchers keep everything in sync automatically — no restart needed:
- **`env_watcher`** — watches `.env`; syncs changed keys to DB, then refreshes in-memory config.
- **`env_local_watcher`** — watches `.env.local`; reloads the in-memory `runtime_config` directly (no DB write).

> See [docs/config-env-db-sync.md](docs/config-env-db-sync.md) for a full technical walkthrough.

---

## Database Migrations

Migrations are managed with **Alembic**.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1

# Create a new migration
uv run alembic revision --autogenerate -m "describe your change"

# Show current migration state
uv run alembic current
```

### Current migrations

| Revision | Description |
|---|---|
| `58937b0f928d` | Create `assets` table |
| `6a5c1b09f820` | Create `app_config` table |

---

## Background Tasks

Three `asyncio` tasks run for the lifetime of the application:

| Task key | Function | Trigger | Purpose |
|---|---|---|---|
| `config_refresher_task` | `config_refresher_task` | Periodic poll (60 s) | Re-reads `app_config` from DB and refreshes in-memory `runtime_config` |
| `env_watcher` | `watch_file_task` + `sync_base_env` | OS file-change event on `.env` | Syncs only changed `.env` keys to DB via `call_sync_env_to_db`, then reloads runtime config |
| `env_local_watcher` | `watch_file_task` + `sync_local_env` | OS file-change event on `.env.local` | Reloads in-memory `runtime_config` directly from disk — no DB write |

All three tasks are started in `on_startup` and gracefully cancelled in `on_cleanup` via `asyncio.gather(return_exceptions=True)`.

The file watchers are powered by the generic **`watch_file_task(path, on_change, ...)`** coroutine, which accepts any async callback via the `on_change` parameter and supports an optional `run_on_start` flag to execute the callback immediately on startup.

> Source: [`app/core/config/config_background_tasks.py`](app/core/config/config_background_tasks.py)

---

## Middleware

Three middlewares run on every request, applied in order:

| Middleware | File | What it does |
|---|---|---|
| `request_id_middleware` | `middleware/request_id.py` | Generates or forwards an `X-Request-ID` UUID; attaches it to the request |
| `error_middleware` | `middleware/error_middleware.py` | Catches unhandled exceptions and returns a structured JSON error response |
| `request_logging_middleware` | `middleware/request_logger.py` | Logs HTTP method, path, response status, and elapsed time |

---

## Documentation

| Topic | File |
|---|---|
| **Env → Database Config Sync** — how `.env` settings are imported to the DB, watched for changes, and kept in sync without duplicate writes | [`docs/config-env-db-sync.md`](docs/config-env-db-sync.md) |
