import asyncio
import logging
import time

from app.repositories.config_repository import fetch_configs

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, settings):
        self.settings = settings
        self.runtime_config = {}

    async def load(self, app):
        async with app["db"].acquire() as conn:
            db_config = await fetch_configs(conn)

        merged = {
            **self.settings.model_dump(),
            **db_config
        }

        self.runtime_config = merged
        logger.info(f"Config Refreshed at {time.time()}")

    def get(self, key, default=None):
        return self.runtime_config.get(key, default)
