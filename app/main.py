import logging
from aiohttp import web

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.postgres import create_db_pool
from app.middleware.request_logger import request_logging_middleware

logger = logging.getLogger(__name__)

async def health(request):
    return web.json_response({"status" : "ok"})

async def on_startup(app):
    logger.info("Creating db pool")
    app["pool"] = await create_db_pool()

async def on_cleanup(app):
    logger.info("Closing db pool")
    await app["pool"].close()

def create_app():
    app = web.Application(
        middlewares=[
            request_logging_middleware,
        ]
    )
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/health", health)
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