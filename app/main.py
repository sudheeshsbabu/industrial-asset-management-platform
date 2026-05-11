import logging
from aiohttp import web

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.postgres import create_db_pool
from app.api.routes.asset_routes import setup_asset_routes
from app.middleware.request_id import request_id_middleware
from app.middleware.error_middleware import error_middleware
from app.middleware.request_logger import request_logging_middleware
from app.core.swagger import setup_swagger

logger = logging.getLogger(__name__)

async def health(request):
    return web.json_response({"status" : "ok"})

async def on_startup(app):
    logger.info("Creating db pool")
    app["db"] = await create_db_pool()

async def on_cleanup(app):
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
    
    if settings.APP_ENVIORNMENT != "prod":
        setup_swagger(app)

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