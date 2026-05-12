from aiohttp import web

from app.api.handlers.common_handler import health

def setup_common_routes(app):
    app.router.add_get('/health', health)