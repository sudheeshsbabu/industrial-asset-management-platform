import os
import time
import asyncio
import logging

from app.repositories.config_repository import sync_env_to_db

logger = logging.getLogger(__name__)

async def config_refresh_task(app):
    """
    Background task: periodically reloads the in-memory runtime config from
    the DB so that any admin-level DB changes are reflected without a restart.
    """
    config_manager = app["config_manager"]
    while True:
        try:
            await config_manager.load(app)
        except asyncio.CancelledError:
            logger.info(f"Config refresh background task cancelled at {time.time()}")
            break
        except Exception as e:
            logger.error(f"Config refresh failed at {time.time()}: {e}")
        await asyncio.sleep(30)

async def env_file_watcher_task(app, env_path: str = ".env", poll_interval: float = 60.0):
    """
    Background task: watches the .env file for modifications by polling its
    last-modified timestamp every `poll_interval` seconds.

    When a change is detected:
      - The Settings class is re-instantiated to reload the latest env values.
      - Only keys whose value differs from what is stored in the DB are written
        (upsert with a WHERE clause guards against duplicate updates).
      - The in-memory runtime config is refreshed immediately after any DB write.

    No action is taken when the file has not changed since the last check.
    """
    # Record the initial mtime so the first poll has a baseline.
    try:
        last_mtime = os.path.getmtime(env_path)
        logger.info(f"Env file watcher started - watching '{env_path}' every {poll_interval}s")
    except FileNotFoundError:
        last_mtime = None
        logger.warning(f"Env file '{env_path}' not found; watcher will retry on each poll")

    while True:
        try:
            await asyncio.sleep(poll_interval)
            try:
                current_mtime = os.path.getmtime(env_path)
            except FileNotFoundError:
                logger.warning(f"Env file '{env_path}' not found; skipping poll")
                continue

            if current_mtime == last_mtime:
                # File unchanged - nothing to do
                continue

            logger.info(f"Env file {env_path} changed {last_mtime} --> {current_mtime}; syncing to DB ...")
            last_mtime = current_mtime

            # --- Reload env settings fresh from the file ---
            # A new Settings() instance re-reads the .env file from disk.
            from app.core.config.config import Settings
            new_settings = Settings()
            env_dict = new_settings.model_dump()
            
            # --- Sync only changed values to DB ---
            async with app["db"].acquire() as conn:
                updated_keys = await sync_env_to_db(conn, env_dict)

            if updated_keys:
                logger.info(f"Env->DB sync: updated keys: {updated_keys}")
                # Refresh in-memory runtime config to pick up the new values
                await app["config_manager"].load(app, new_settings=new_settings)
            else:
                logger.info("Env->DB sync: no value changes detected, DB left unchanged")

        except asyncio.CancelledError:
            logger.info(f"Env file watcher task cancelled at {time.time()}")
            break
        except Exception as e:
            logger.error(f"Env file watcher error: {e}")