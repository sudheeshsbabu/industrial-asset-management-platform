# Env → Database Config Sync

> **Related feature area:** `app/core/config/` · `app/repositories/config_repository.py`  
> **Entry point:** [`app/main.py`](../app/main.py)

---

## Overview

This feature automatically mirrors every setting defined in the `.env` file into
the `app_config` PostgreSQL table and keeps the two in sync at runtime — without
ever writing a value twice if nothing has changed.

Two complementary mechanisms work together:

| Mechanism | When it runs | What it does |
|---|---|---|
| **Env file watcher** | Continuously (every 60 s) | Detects `.env` file changes → upserts only the changed keys to DB → refreshes runtime config |
| **DB config refresher** | Continuously (every 60 s) | Re-reads `app_config` from DB → merges with env defaults → updates in-memory runtime config |

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
├── __init__(settings)     – stores the Settings instance, starts with empty runtime_config
├── load(app, new_settings?)  – fetches DB, merges env + DB, stores in runtime_config
├── import_from_env(app)   – dumps settings → sync_env_to_db (startup seed)
└── get(key, default)      – read a runtime value by key
```

#### `load(app, new_settings=None)`

```
env defaults (Settings.model_dump())
    +
DB overrides (fetch_db_configs)        ← DB wins on conflict
    =
runtime_config dict
```

The optional `new_settings` parameter lets the env-file watcher pass a freshly
re-instantiated `Settings` object so the updated env values are reflected in
`runtime_config` immediately after a sync.

#### `import_from_env(app)`

> **Note:** This method exists on `ConfigManager` but is **not called in `on_startup` in the
> current version of `main.py`**. The initial env→DB sync is instead performed
> inside `env_file_watcher_task` on first start (see §5 below). `import_from_env`
> can be called explicitly if a one-shot startup seed is preferred.

---

### 5. Background Tasks — `config_background_tasks.py`

**File:** [`app/core/config/config_background_tasks.py`](../app/core/config/config_background_tasks.py)

Two long-running `asyncio` coroutines are created as tasks in `on_startup`.

---

#### `config_refresher_task(app, poll_interval=60s)`

```
loop every 60 s:
    ConfigManager.load(app)
        → fetch app_config from DB
        → merge with current env defaults
        → update runtime_config in memory
```

Purpose: picks up any **manual changes made directly in the DB** (e.g. via `psql` or an admin tool) without restarting the application.

---

#### `env_file_watcher_task(app, env_path=".env", poll_interval=60s)`

```
on startup:
    record .env mtime as baseline
    call call_sync_env_to_db(app)   ← initial import

loop every 60 s:
    read current mtime of .env
    if mtime == last_mtime  →  skip (no change)
    else:
        update last_mtime
        call call_sync_env_to_db(app)
```

#### Helper — `call_sync_env_to_db(app)`

Called both at startup and after every detected file change:

```
Settings()                     ← re-reads .env from disk
    ↓  model_dump()
sync_env_to_db(conn, env_dict) ← upsert only changed keys
    ↓  if any updated_keys
ConfigManager.load(app, new_settings)  ← refresh runtime_config immediately
```

**If nothing changed** in the file since last poll, `upsert_config` returns `False` for every key and no DB write occurs. `updated_at` is not touched.

---

### 6. Application Wiring — `main.py`

**File:** [`app/main.py`](../app/main.py)

```python
async def on_startup(app):
    app["db"] = await create_db_pool()

    config_manager = ConfigManager(settings)
    await config_manager.load(app)          # initial in-memory load
    app["config_manager"] = config_manager

    # Task 1: re-read DB → update runtime_config every 60 s
    app["config_refresher_task"] = asyncio.create_task(config_refresher_task(app))

    # Task 2: watch .env → sync changed keys to DB → update runtime_config
    app["env_file_watcher_task"] = asyncio.create_task(env_file_watcher_task(app))
```

```python
async def on_cleanup(app):
    app["config_refresher_task"].cancel()
    app["env_file_watcher_task"].cancel()
    await asyncio.gather(
        app["config_refresher_task"],
        app["env_file_watcher_task"],
        return_exceptions=True
    )
    await app["db"].close()
```

> **Note:** `Task.cancel()` returns a `bool` and is not awaitable. The `await` before
> each `.cancel()` call in the current code is a no-op (Python silently awaits the bool `True`
> as a coroutine-like but it does not cause an error). The `asyncio.gather` below is
> what actually waits for both tasks to finish their `CancelledError` handling.

---

## End-to-End Flow Diagrams

### Startup

```
app starts
    │
    ├─ create_db_pool()
    │
    ├─ ConfigManager(settings)
    │       └─ load(app)
    │               ├─ fetch_db_configs()   → reads current app_config table
    │               └─ runtime_config = {**env_defaults, **db_rows}
    │
    ├─ asyncio.create_task(config_refresher_task)
    │
    └─ asyncio.create_task(env_file_watcher_task)
                │
                └─ call_sync_env_to_db()  ← initial .env → DB import
                        ├─ Settings()     ← re-reads .env
                        ├─ sync_env_to_db()
                        │       └─ upsert_config() × N keys
                        │               (skips keys already matching)
                        └─ ConfigManager.load(app, new_settings)
```

### .env File Changed at Runtime

```
.env edited by developer/ops
    │
    ├─ (up to 60 s later) env_file_watcher_task wakes up
    │
    ├─ os.path.getmtime(".env") != last_mtime  →  change detected
    │
    └─ call_sync_env_to_db(app)
            ├─ Settings()            ← new instance reads updated .env
            ├─ model_dump()          → {"APP_PORT": 9090, ...}
            ├─ sync_env_to_db()
            │       └─ upsert_config("APP_PORT", "9090")
            │               SQL: INSERT … ON CONFLICT DO UPDATE WHERE value != '9090'
            │               → value changed: write occurs, RETURNING key → True
            │
            │       └─ upsert_config("APP_NAME", "AssetOps")
            │               → value unchanged: WHERE clause suppresses write → False
            │
            ├─ updated_keys = ["APP_PORT"]   (only the changed key)
            └─ ConfigManager.load(app, new_settings)
                    └─ runtime_config["APP_PORT"] = "9090"
```

### No Change Detected

```
env_file_watcher_task wakes up
    │
    └─ mtime == last_mtime  →  continue (sleep again, zero DB activity)
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

### File change detection uses mtime polling (not inotify)

`os.path.getmtime()` works cross-platform (Linux, macOS, Windows) and requires no
OS-level file-watch API. The trade-off is a maximum 60-second lag between a file
edit and the sync. Adjust `poll_interval` in `env_file_watcher_task` if faster
detection is needed.

---

## File Map

| File | Role |
|---|---|
| [`.env`](../.env) | Source of truth for environment-specific settings |
| [`app/core/config/config.py`](../app/core/config/config.py) | `Settings` model (pydantic-settings); maps env vars to typed fields |
| [`app/core/config/config_manager.py`](../app/core/config/config_manager.py) | `ConfigManager` — holds `runtime_config`, orchestrates load & import |
| [`app/core/config/config_background_tasks.py`](../app/core/config/config_background_tasks.py) | `config_refresher_task` + `env_file_watcher_task` + `call_sync_env_to_db` |
| [`app/repositories/config_repository.py`](../app/repositories/config_repository.py) | All SQL for `app_config` — fetch, upsert, sync |
| [`migrations/versions/6a5c1b09f820_create_app_config_table.py`](../migrations/versions/6a5c1b09f820_create_app_config_table.py) | Alembic migration that creates the `app_config` table |
| [`app/main.py`](../app/main.py) | Wires tasks into aiohttp lifecycle (`on_startup` / `on_cleanup`) |
