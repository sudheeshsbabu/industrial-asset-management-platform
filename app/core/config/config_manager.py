import asyncio
import logging
import time

from app.core.config.config import Settings

from app.repositories.config_repository import (
    fetch_db_configs,
    sync_env_to_db
)

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.settings = {}
        self.runtime_config = {}

    async def load(self, app):
        """Refresh the in-memory runtime config from the DB (DB values override env defaults)."""

        # Load local settings
        self.load_local_settings()

        async with app["db"].acquire() as conn:
            db_config = await fetch_db_configs(conn)

        merged = {
            **db_config,
            **self.settings.model_dump(), # load_local_settings() overrides the  db & env settings
        }

        self.runtime_config = merged
        logger.info(f"Config Refreshed at {time.time()} with values : {self.settings.model_dump()}")

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

    def load_local_settings(self):
        """Load local settings from the .env.local file."""
        self.settings = Settings(
            _env_file=[".env", ".env.local"]
        )
