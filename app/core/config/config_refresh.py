import time
import asyncio
import logging

logger = logging.getLogger(__name__)

async def config_refresh_task(app):
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