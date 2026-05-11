from aiohttp import web
from pydantic import ValidationError

from app.models.asset import (
    AssetCreate,
    AssetResponse
)

from app.services.asset_services import (
    list_assets,
    fetch_asset,
    add_asset
)

async def get_assets(request):
    async with request.app['db'].acquire() as conn:
        assets = await list_assets(conn)
    return web.json_response([
        AssetResponse(
            **dict(asset)
        ).model_dump() 
        for asset in assets
    ])

async def get_asset(request):
    asset_id = int(request.match_info.get("id"))
    async with request.app['db'].acquire() as conn:
        asset = await fetch_asset(conn, asset_id)

    return web.json_response(
        AssetResponse(
            **dict(asset)
        ).model_dump()
    )

async def create_asset_handler(request):
    try:
        payload = await request.json()
        data = AssetCreate(**payload)
    except ValidationError as e:
        return web.json_response({
            "error": e.errors()
        }, status=400)

    async with request.app['db'].acquire() as conn:
        asset = await add_asset(conn, data)

    return web.json_response(
        dict(asset),
        status=201
    )
    