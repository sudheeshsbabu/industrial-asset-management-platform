# Env → Database Config Sync

> **Related feature area:** `app/core/config/` · `app/repositories/config_repository.py`  
> **Entry point:** [`app/main.py`](../app/main.py)

---

## The Core Idea — Zero-Restart Config Updates

> The application **never needs to be restarted** to pick up a configuration change.
> Edit `.env` or `.env.local` (or update the DB directly) and the running app reflects
> the new values within milliseconds.

The system uses three layered sources of truth:

```
┌─────────────────────────────────────────────────────────────────┐
│  Priority (lowest → highest)                                    │
│                                                                 │
│   DB (app_config table)                                         │
│          ↑  upserted from .env on startup / on .env change      │
│   .env   (base settings)                                        │
│          ↑  overridden by .env.local when both exist            │
│   .env.local  (local developer overrides)                       │
│          │                                                      │
│          ▼  ConfigManager.load_local_settings()                 │
│   runtime_config (in-memory merged dict)                        │
│          │                                                      │
│          ▼                                                      │
│   App serves config on every request                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Three key properties fall out of this design:**

| Property | How it is achieved |
|---|---|
| **Instant propagation** | Both triggers are event-based — OS file-watch + PG NOTIFY. No timer fires; no sleep wakes up. |
| **No duplicate writes** | The SQL `ON CONFLICT … WHERE value != EXCLUDED.value` guard means unchanged keys never touch the DB. |
| **Admin override survives restarts** | DB values take precedence over `.env` defaults in `runtime_config`, so a value set directly in the DB is preserved even if `.env` is later saved with the old value. |

> **Direct DB edit path:** An operator can also `UPDATE app_config SET value = '…'` directly in `psql`. The same PG NOTIFY trigger fires (step 4 above) and the app picks it up immediately — no `.env` change needed.

---

## Overview

This feature automatically mirrors every setting defined in `.env` into the
`app_config` PostgreSQL table and keeps everything in sync at runtime — without
ever writing a value twice if nothing has changed.

Three complementary mechanisms work together:

| Mechanism | Task key | When it runs | What it does |
|---|---|---|---|
| **Base env watcher** | `env_watcher` | OS file-change event on `.env` | Upserts only changed keys to DB via `sync_base_env` → refreshes runtime config |
| **Local env watcher** | `env_local_watcher` | OS file-change event on `.env.local` | Reloads in-memory settings via `sync_local_env` — no DB write |
| **DB config refresher** | `config_refresher_task` | Periodic poll (60 s) | Re-reads `app_config` from DB → updates runtime config |

---


## Architecture at a Glance

```
.env file
   │
   │  read by pydantic-settings
   ▼
Settings (config.py)          ◄── single source of truth for typed env values
   │
   │  model_dump()
   ▼
sync_env_to_db()              ◄── config_repository.py
   │
   │  upsert_config() per key (SQL: INSERT … ON CONFLICT … WHERE value != …)
   ▼
app_config table (PostgreSQL)
   │
   │  fetch_db_configs()
   ▼
ConfigManager.runtime_config  ◄── merged dict used by the rest of the app
```

---

## Component Walkthrough

### 1. Database Table — `app_config`

**File:** [`migrations/versions/6a5c1b09f820_create_app_config_table.py`](../migrations/versions/6a5c1b09f820_create_app_config_table.py)

```sql
CREATE TABLE app_config (
    id         SERIAL PRIMARY KEY,
    key        VARCHAR(100) NOT NULL UNIQUE,   -- e.g. "APP_PORT"
    value      VARCHAR(255) NOT NULL,          -- always stored as a string
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()         -- updated only on real changes
);
```

- `key` has a `UNIQUE` constraint — this is what the `ON CONFLICT` upsert targets.
- `updated_at` is only changed when the value actually differs (enforced in SQL).

---

### 2. Settings Model — `config.py`

**File:** [`app/core/config/config.py`](../app/core/config/config.py)

```python
class Settings(BaseSettings):
    APP_NAME: str = "AssetOps"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    DB_HOST:  str = "localhost"
    DB_PORT:  int = 5432
    DB_NAME:  str = "assetops"
    DB_USER:  str = "postgres"
    DB_PASSWORD: str = "postgres"

    class Config:
        env_file = ".env"
```

- Backed by **pydantic-settings** — instantiating `Settings()` always re-reads the `.env` file from disk.
- `model_dump()` produces the flat `{"KEY": value, …}` dict that is fed into the sync pipeline.

---

### 3. Repository Layer — `config_repository.py`

**File:** [`app/repositories/config_repository.py`](../app/repositories/config_repository.py)

This file owns all SQL for the `app_config` table.

#### `fetch_db_configs(conn) → dict`

```python
SELECT key, value FROM app_config
```

Returns the entire table as `{"KEY": "value", …}`. Used by `ConfigManager.load()` to build the in-memory runtime config.

#### `upsert_config(conn, key, value) → bool`

The heart of the duplicate-prevention mechanism:

```sql
INSERT INTO app_config (key, value)
VALUES ($1, $2)
ON CONFLICT (key) DO UPDATE
    SET value      = EXCLUDED.value,
        updated_at = NOW()
WHERE app_config.value != EXCLUDED.value   -- ← guard: skip if identical
RETURNING key
```

- If the key **doesn't exist** → inserts a new row, returns `True`.
- If the key **exists with a different value** → updates it, returns `True`.
- If the key **exists with the same value** → the `WHERE` clause suppresses the update; `RETURNING` yields no row → returns `False`.

No Python-level comparison needed — the database itself is the gate.

#### `sync_env_to_db(conn, env_dict) → list[str]`

Iterates over every key/value pair from `Settings.model_dump()` and calls `upsert_config` for each. Returns the list of keys that were **actually written** (empty list = nothing changed).

---

### 4. Config Manager — `config_manager.py`

**File:** [`app/core/config/config_manager.py`](../app/core/config/config_manager.py)

```
ConfigManager
├── __init__()               – no args; runtime_config starts empty
├── load(app)                – calls load_local_settings(), fetches DB, merges, stores runtime_config
├── load_local_settings()    – re-instantiates Settings(['.env', '.env.local'])
├── import_from_env(app)     – dumps settings → sync_env_to_db (startup seed, on-demand)
└── get(key, default)        – read a runtime value by key
```

#### `load(app)`

```
load_local_settings()
    Settings(_env_file=[".env", ".env.local"])   ← .env.local wins on conflict

DB rows (fetch_db_configs)    ← loaded first (lower priority)
    +
local settings model_dump()   ← overlaid on top (higher priority)
    =
runtime_config dict
```

**Priority reversal vs. earlier design:** DB values no longer win over env values.
Local settings (including `.env.local` overrides) always take the highest precedence
in `runtime_config`. The DB remains the source of truth for admin-edited values that
have no corresponding `.env` entry.

#### `import_from_env(app)`

> **Note:** This is available for a one-shot startup seed but is not called
> directly in `on_startup`. The initial `.env → DB` sync is performed by
> `env_watcher` at startup via `run_on_start=True` (see §5 below).

---

### 5. Background Tasks — `config_background_tasks.py`

**File:** [`app/core/config/config_background_tasks.py`](../app/core/config/config_background_tasks.py)

Three long-running `asyncio` tasks are created in `on_startup`.

---

#### `config_refresher_task(app, polling_secs=60)`

```
every 60 seconds:
    ConfigManager.load(app)
        → load_local_settings()   ← re-reads .env + .env.local
        → fetch app_config from DB
        → merge → update runtime_config
```

Purpose: periodically reconciles in-memory config with the DB, picking up any
**admin changes made directly** in the `app_config` table.

---

#### `watch_file_task(path, on_change, task_name, run_on_start)` — generic watcher

A reusable coroutine that watches any file for OS-level change events and invokes
an async callback. Used for both env file watchers.

```
if run_on_start:
    await onchange_callback(on_change)   ← runs callback immediately on startup

wait for OS file-change event (watchfiles / native OS API):
    on modified or added event:
        await onchange_callback(on_change)
    on deleted / other events:
        skip
```

`onchange_callback` is a nested async helper that wraps the callback with
`FileNotFoundError` and generic exception handling.

`watchfiles` uses **ReadDirectoryChangesW** on Windows, **inotify** on Linux,
and **FSEvents** on macOS — zero polling, instant notification.

---

#### `sync_base_env(app)` — callback for `env_watcher`

```
await call_sync_env_to_db(app)
    → Settings()              ← re-reads .env from disk
    → sync_env_to_db()        ← upsert only changed keys
    → ConfigManager.load(app) ← refresh runtime_config if anything changed
```

#### `sync_local_env(app)` — callback for `env_local_watcher`

```
await ConfigManager.load(app)
    → load_local_settings()   ← re-reads .env + .env.local
    → merge with DB rows
    → update runtime_config
```

No DB write occurs — this path only refreshes the in-memory config.

#### Helper — `call_sync_env_to_db(app)`

```
Settings()                     ← re-reads .env from disk
    ↓  model_dump()
sync_env_to_db(conn, env_dict) ← upsert only changed keys
    ↓  if any updated_keys
ConfigManager.load(app)        ← refresh runtime_config immediately
```

**If nothing changed**, `upsert_config` returns `False` for every key — no DB write,
`updated_at` is not touched.

---

### 6. Application Wiring — `main.py`

**File:** [`app/main.py`](../app/main.py)

```python
async def on_startup(app):
    app["db"] = await create_db_pool()

    config_manager = ConfigManager()        # no args — reads .env + .env.local internally
    await config_manager.load(app)          # initial in-memory load
    app["config_manager"] = config_manager

    # Task 1: periodic DB poll → update runtime_config
    app["config_refresher_task"] = asyncio.create_task(
        config_refresher_task(app)
    )

    # Task 2: watch .env → sync changed keys to DB → refresh runtime_config
    app["env_watcher"] = asyncio.create_task(
        watch_file_task(
            path=".env",
            on_change=lambda: sync_base_env(app),
            task_name="base_env_watcher",
            run_on_start=True,
        )
    )

    # Task 3: watch .env.local → reload in-memory settings (no DB write)
    app["env_local_watcher"] = asyncio.create_task(
        watch_file_task(
            path=".env.local",
            on_change=lambda: sync_local_env(app),
            task_name="local_env_watcher",
            run_on_start=True,
        )
    )
```

```python
async def on_cleanup(app):
    app["config_refresher_task"].cancel()
    app["env_watcher"].cancel()
    app["env_local_watcher"].cancel()
    await asyncio.gather(
        app["config_refresher_task"],
        app["env_watcher"],
        app["env_local_watcher"],
        return_exceptions=True
    )
    await app["db"].close()
```

---

## End-to-End Flow Diagrams

### Startup

```
app starts
    │
    ├─ create_db_pool()
    │
    ├─ ConfigManager()                        ← no args
    │       └─ load(app)
    │               ├─ load_local_settings()  ← Settings(['.env', '.env.local'])
    │               ├─ fetch_db_configs()     → reads current app_config table
    │               └─ runtime_config = {**db_rows, **local_settings}  ← local wins
    │
    ├─ asyncio.create_task(config_refresher_task)      → polls DB every 60s
    │
    ├─ asyncio.create_task(watch_file_task '.env')     → env_watcher
    │       └─ run_on_start=True → sync_base_env(app)
    │               └─ call_sync_env_to_db()
    │                       ├─ Settings()     ← re-reads .env
    │                       ├─ sync_env_to_db() → upsert_config() × N keys
    │                       └─ ConfigManager.load(app) if any keys changed
    │
    └─ asyncio.create_task(watch_file_task '.env.local')  → env_local_watcher
            └─ run_on_start=True → sync_local_env(app)
                    └─ ConfigManager.load(app)  ← re-reads .env + .env.local
```

### `.env` File Changed at Runtime

```
.env edited by developer/ops
    │
    ├─ OS emits file-change event  →  watchfiles awatch() yields immediately
    │
    └─ sync_base_env(app) → call_sync_env_to_db(app)
            ├─ Settings()            ← new instance reads updated .env
            ├─ model_dump()          → {"APP_PORT": 9090, ...}
            ├─ sync_env_to_db()
            │       └─ upsert_config("APP_PORT", "9090")
            │               → value changed: write occurs → True
            │       └─ upsert_config("APP_NAME", "AssetOps")
            │               → value unchanged: WHERE clause suppresses write → False
            │
            ├─ updated_keys = ["APP_PORT"]
            └─ ConfigManager.load(app)
                    └─ runtime_config["APP_PORT"] = "9090"
```

### `.env.local` File Changed at Runtime

```
.env.local edited by developer
    │
    ├─ OS emits file-change event  →  watchfiles awatch() yields immediately
    │
    └─ sync_local_env(app)
            └─ ConfigManager.load(app)
                    ├─ load_local_settings()   ← re-reads .env + .env.local
                    ├─ fetch_db_configs()       ← reads DB
                    └─ runtime_config = {**db_rows, **local_settings}
                            (no DB write — only in-memory update)
```



---

## Key Design Decisions

### Duplicate-prevention is enforced at the SQL layer

The `WHERE app_config.value != EXCLUDED.value` clause inside the `ON CONFLICT`
block means the database itself refuses to write when the value is unchanged.
This avoids:
- Unnecessary row churn / WAL entries in Postgres
- Spurious `updated_at` timestamp bumps
- Any need for a Python-side "read-compare-write" pattern (which would require locking)

### DB values take precedence over env values in runtime config

In `ConfigManager.load()`:
```python
merged = {
    **self.settings.model_dump(),   # env defaults (lower priority)
    **db_config                     # DB overrides (higher priority)
}
```

This means an operator can override any env setting directly in the DB and the
application respects it without a file change or restart.

### File change detection uses OS-native events (watchfiles)

`watchfiles` wraps the OS-native file-watch API on each platform — **inotify** on
Linux, **FSEvents** on macOS, **ReadDirectoryChangesW** on Windows. Changes are
delivered instantly with no polling lag and zero CPU overhead while the file is
unchanged. The `awatch()` async generator integrates natively with asyncio's event
loop.

---

## File Map

| File | Role |
|---|---|
| [`.env`](../.env) | Base environment settings (never commit secrets) |
| [`.env.local`](../.env.local) | Local developer overrides — highest priority, not committed |
| [`app/core/config/config.py`](../app/core/config/config.py) | `Settings` model (pydantic-settings); maps env vars to typed fields |
| [`app/core/config/config_manager.py`](../app/core/config/config_manager.py) | `ConfigManager` — `load()`, `load_local_settings()`, `import_from_env()`, `get()` |
| [`app/core/config/config_background_tasks.py`](../app/core/config/config_background_tasks.py) | `watch_file_task`, `sync_base_env`, `sync_local_env`, `call_sync_env_to_db`, `config_refresher_task` |
| [`app/repositories/config_repository.py`](../app/repositories/config_repository.py) | All SQL for `app_config` — fetch, upsert, sync |
| [`migrations/versions/6a5c1b09f820_create_app_config_table.py`](../migrations/versions/6a5c1b09f820_create_app_config_table.py) | Alembic migration: creates the `app_config` table |
| [`migrations/versions/7b6d2c10e931_add_notify_trigger_to_app_config.py`](../migrations/versions/7b6d2c10e931_add_notify_trigger_to_app_config.py) | Alembic migration: adds PG trigger + `NOTIFY` function on `app_config` |
| [`app/main.py`](../app/main.py) | Wires tasks into aiohttp lifecycle (`on_startup` / `on_cleanup`) |
