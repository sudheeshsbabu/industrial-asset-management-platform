import time
import asyncio
import logging

from watchfiles import awatch, Change

from app.repositories.config_repository import sync_env_to_db

logger = logging.getLogger(__name__)

async def config_refresher_task(app, channel: str = "app_config_changed"):
    """
    Background task: listens for PostgreSQL notifications on the specified channel
    to reload the in-memory runtime config immediately when DB changes occur.
    """
    config_manager = app["config_manager"]
    loop = asyncio.get_running_loop()
    event = asyncio.Event()

    def on_notification(conn, pid, channel, payload):
        logger.info(f"Received DB notification on channel '{channel}'; scheduling config reload.")
        loop.call_soon_threadsafe(event.set)

    pool = app["db"]

    while True:
        try:
            async with pool.acquire() as conn:
                await conn.add_listener(channel, on_notification)
                logger.info(f"Config refresher subscribed to DB channel '{channel}'")
                try:
                    while True:
                        await event.wait()
                        event.clear()
                        try:
                            await config_manager.load(app)
                        except Exception as e:
                            logger.error(f"Config refresh failed upon notification at {time.time()}: {e}")
                finally:
                    try:
                        await conn.remove_listener(channel, on_notification)
                    except Exception as e:
                        logger.debug(f"Error removing listener on cleanup: {e}")
        except asyncio.CancelledError:
            logger.info(f"Config refresh background task cancelled at {time.time()}")
            break
        except Exception as e:
            logger.error(f"Config refresh listener connection error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5.0)

async def env_file_watcher_task(app, env_path: str = ".env"):
    """
    Background task: watches the .env file for real filesystem events using
    `watchfiles` (backed by native OS file-watch APIs — inotify on Linux,
    FSEvents on macOS, ReadDirectoryChangesW on Windows).

    Reacts immediately when a write/modify event is detected:
      - The Settings class is re-instantiated to reload the latest env values.
      - Only keys whose value differs from what is stored in the DB are written
        (upsert with a WHERE clause guards against duplicate updates).
      - The in-memory runtime config is refreshed immediately after any DB write.

    No action is taken for file deletions or other non-modify events.
    """
    # Perform initial sync of env to DB on startup.
    try:
        await call_sync_env_to_db(app)
    except FileNotFoundError:
        logger.warning(f"Env file '{env_path}' not found on startup; watcher will still wait for it to appear")
    except Exception as e:
        logger.error(f"Initial env->DB sync failed: {e}")

    logger.info(f"Env file watcher started - watching '{env_path}' for OS-level change events")

    try:
        async for changes in awatch(env_path):
            # changes is a set of (Change, path) tuples.
            # We only care about modifications (not deletions).
            relevant = {path for change_type, path in changes if change_type in (Change.modified, Change.added)}
            if not relevant:
                continue

            logger.info(f"Env file '{env_path}' changed (event: {changes}); syncing to DB ...")
            try:
                await call_sync_env_to_db(app)
            except Exception as e:
                logger.error(f"Env->DB sync failed after file change event: {e}")

    except asyncio.CancelledError:
        logger.info(f"Env file watcher task cancelled at {time.time()}")
    except Exception as e:
        logger.error(f"Env file watcher encountered a fatal error: {e}")

async def call_sync_env_to_db(app):
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