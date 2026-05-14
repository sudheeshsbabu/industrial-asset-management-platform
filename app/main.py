import asyncio
import logging
from aiohttp import web

from app.db.postgres import create_db_pool
from app.core.logging import setup_logging
from app.api.routes.asset_routes import setup_asset_routes
from app.api.routes.common_routes import setup_common_routes

from app.middleware.request_id import request_id_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.request_logger import request_logging_middleware

from app.core.config.config import settings
from app.core.config.config_manager import ConfigManager
from app.core.config.config_background_tasks import (
    PollingRefreshStrategy,
    watch_file_task,
    sync_local_env,
    sync_base_env
)

from app.services.asset_services import AssetService
from app.services.config_services import ConfigService
from app.repositories.asset_repository import PostgresAssetRepository
from app.repositories.config_repository import PostgresConfigRepository

logger = logging.getLogger(__name__)

async def on_startup(app):
    app["db"] = await create_db_pool()

    app["asset_service_factory"] = lambda conn: AssetService(
        repo=PostgresAssetRepository(conn)
    )
    app["config_service_factory"] = lambda conn: ConfigService(
        repo=PostgresConfigRepository(conn)
    )

    config_manager = ConfigManager()
    await config_manager.load(app)

    app["config_manager"] = config_manager
    
    # Strategy 1: DB Polling
    strategy = PollingRefreshStrategy()
    app["config_refresher_task"] = asyncio.create_task(
        strategy.run(app)
    )
    
    # Watch .env file for changes and sync only updated values to DB.
    app["env_watcher"] = asyncio.create_task(
        watch_file_task(
            task_name="base_env_watcher",
            run_on_start=True,
            path=".env",
            on_change= lambda: sync_base_env(app)
        )
    )

    # Watch .env.local file for changes and sync with in-memory settings.
    app["env_local_watcher"] = asyncio.create_task(
        watch_file_task(
            task_name="local_env_watcher",
            run_on_start=True,
            path=".env.local",
            on_change= lambda: sync_local_env(app)
        )
    )

async def on_cleanup(app):
    logger.info("Cancelling background tasks")
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


def create_app():
    app = web.Application(
        middlewares=[
            request_id_middleware,
            error_middleware,
            request_logging_middleware
        ]
    )

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    setup_asset_routes(app)
    setup_common_routes(app)

    return app

if __name__ == "__main__":
    setup_logging()
    app = create_app()

    web.run_app(
        app=app, 
        host=settings.APP_HOST, 
        port=settings.APP_PORT
    )