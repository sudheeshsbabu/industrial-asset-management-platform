import time
import asyncio
import logging
from collections.abc import Callable, Awaitable
from watchfiles import awatch, Change

logger = logging.getLogger(__name__)

async def config_refresher_task(app, polling_secs: int = 60):
    """
    Background task: polls the database every 60 seconds to reload the in-memory runtime config.
    """
    config_manager = app["config_manager"]
    pool = app["db"]

    while True:
        try:
            async with pool.acquire() as conn:
                await config_manager.load(app)
            await asyncio.sleep(polling_secs)
        except asyncio.CancelledError:
            logger.info(f"Config Polling Task cancelled at {time.time()}")
            break
        except Exception as e:
            logger.error(f"Config Polling Task encountered an error at {time.time()}: {e}. Retrying in {polling_secs}")
            await asyncio.sleep(polling_secs)

async def config_refresher_task_with_db_trigger(app, channel: str = "app_config_changed"):
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

async def call_sync_env_to_db(app):
    # --- Reload env settings fresh from the file ---
    
    # A new Settings() instance re-reads the .env file from disk.
    from app.core.config.config import Settings
    new_settings = Settings()
    env_dict = new_settings.model_dump()
    
    # --- Sync only changed values to DB ---
    async with app["db"].acquire() as conn:
        service = app["config_service_factory"](conn)
        updated_keys = await service.sync_dict(env_dict)

    if updated_keys:
        logger.info(f"Env->DB sync: updated keys: {updated_keys}")
        # Not required as per the new requirement. 
        # await app["config_manager"].load(app)
    else:
        logger.info("Env->DB sync: no value changes detected, DB left unchanged")

async def watch_file_task(
    path: str,
    on_change: Callable[[], Awaitable[None]],
    task_name: str = "file_watcher",
    run_on_start: bool = True,
    *args,
    **kwargs,
):
    """
    Generic async file watcher using watchfiles.

    - Watches a file using native OS events.
    - Executes a callback whenever the file is modified/created.
    - Optional initial startup execution.
    """
    async def onchange_callback(
        on_change_func: Callable[[], Awaitable[None]],
        *args, 
        **kwargs
    ):
        try:
            await on_change_func(*args, **kwargs)
        except FileNotFoundError:
            logger.warning(f"{task_name}: {path} file not found at startup")
        except Exception as e:
            logger.exception(f"{task_name} startup callback failed: {e}")

    if run_on_start:
        await onchange_callback(on_change, *args, **kwargs)
    logger.info(f"{task_name} started - watching '{path}' for changes")
    
    try:
        async for changes in awatch(path):
            relevant = {
                file_path
                for change_type, file_path in changes
                if change_type in (Change.modified, Change.added)
            }
            if not relevant:
                continue

            logger.info(f"{task_name}: file changed (event: {changes}); invoking callback")
            await onchange_callback(on_change, *args, **kwargs)

    except asyncio.CancelledError:
        logger.info(f"{task_name} cancelled at {time.time()}")
    except Exception as e:
        logger.error(f"{task_name} encountered a fatal error: {e}")

async def sync_base_env(app):
    await call_sync_env_to_db(app)

async def sync_local_env(app):
    try:
        await app["config_manager"].load(app)
    except Exception as e:
        logger.error(f"local env update failed: {e}")