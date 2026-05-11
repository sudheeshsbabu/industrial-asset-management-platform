import logging
from aiohttp import web

from app.core.config import settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

async def health(request):
    return web.json_response({"status" : "ok"})

def create_app():
    app = web.Application()
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