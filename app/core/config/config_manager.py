import asyncio
import logging
import time

from app.repositories.config_repository import (
    fetch_db_configs,
    sync_env_to_db
)

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, settings):
        self.settings = settings
        self.runtime_config = {}

    async def load(self, app, new_settings=None):
        """Refresh the in-memory runtime config from the DB (DB values override env defaults)."""
        if new_settings:
            self.settings = new_settings # override the env settings with the new settings

        async with app["db"].acquire() as conn:
            db_config = await fetch_db_configs(conn)

        merged = {
            **self.settings.model_dump(),
            **db_config # db config takes presedence over env config
        }

        self.runtime_config = merged
        logger.info(f"Config Refreshed at {time.time()}")

    def get(self, key, default=None):
        return self.runtime_config.get(key, default)

    async def import_from_env(self, app):
        """
        Seed the DB with all settings loaded from the env file.
        Only inserts or updates entries whose value has actually changed ΓÇö
        duplicate writes are skipped at the SQL level.
        Called once on application startup.
        """
        env_dict = self.settings.model_dump()
        async with app["db"].acquire() as conn:
            updated_keys = await sync_env_to_db(conn, env_dict)
        
        if updated_keys:
            logger.info(f"Env->DB Import: inserted/updated keys: {updated_keys}")
        else:
            logger.info("Env->DB Import: All settings already up to date, no changes needed.")
