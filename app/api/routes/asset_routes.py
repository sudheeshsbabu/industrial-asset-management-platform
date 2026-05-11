from aiohttp import web

from app.api.handlers.asset_handler import (
    get_assets,
    get_asset,
    create_asset_handler
)

def setup_asset_routes(app):
    app.router.add_get('/assets', get_assets)
    app.router.add_get('/assets/{id}', get_asset)
    app.router.add_post('/assets', create_asset_handler)