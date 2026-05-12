import asyncio
import logging
from aiohttp import web

from app.db.postgres import create_db_pool
from app.core.logging import setup_logging
from app.api.routes.asset_routes import setup_asset_routes

from app.middleware.request_id import request_id_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.request_logger import request_logging_middleware

from app.core.config.config import settings
from app.core.config.config_manager import ConfigManager
from app.core.config.config_refresh import (
    config_refresh_task,
    env_file_watcher_task
)

logger = logging.getLogger(__name__)

async def health(request):
    return web.json_response({"status" : "ok"})

async def on_startup(app):
    logger.info("Creating db pool")
    app["db"] = await create_db_pool()

    config_manager = ConfigManager(settings)
    await config_manager.load(app)

    app["config_manager"] = config_manager
    
    # Periodically re-read runtime config from DB (picks up admin-level DB edits).
    app["config_background_task"] = asyncio.create_task(
        config_refresh_task(app)
    )
    
    # Watch .env file for changes and sync only updated values to DB.
    app["env_file_watcher_task"] = asyncio.create_task(
        env_file_watcher_task(app)
    )

async def on_cleanup(app):
    logger.info("Cancelling background tasks")
    await app["config_background_task"].cancel()
    await app["env_file_watcher_task"].cancel()
    
    await asyncio.gather(
        app["config_background_task"],
        app["env_file_watcher_task"],
        return_exceptions=True
    )

    logger.info("Closing db pool")
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

    app.router.add_get("/health", health)
    setup_asset_routes(app)

    return app

if __name__ == "__main__":
    setup_logging()
    logger.info(f"Starting app")
    app = create_app()

    web.run_app(
        app=app, 
        host=settings.APP_HOST, 
        port=settings.APP_PORT
    )