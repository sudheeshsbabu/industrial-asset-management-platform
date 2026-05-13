from aiohttp import web

from app.models.asset import AssetCreate

async def get_assets(request):
    async with request.app['db'].acquire() as conn:
        service = request.app["asset_service_factory"](conn)
        assets = await service.list_assets()
    return web.json_response([
        asset.model_dump() for asset in assets
    ])

async def get_asset(request):
    asset_id = int(request.match_info.get("id"))
    async with request.app['db'].acquire() as conn:
        service = request.app["asset_service_factory"](conn)
        asset = await service.fetch_asset(asset_id)
    return web.json_response(
        asset.model_dump()
    )

async def create_asset_handler(request):
    payload = await request.json()
    data = AssetCreate(**payload)

    async with request.app['db'].acquire() as conn:
        service = request.app["asset_service_factory"](conn)
        asset = await service.add_asset(data)

    return web.json_response(
        {
            "success": True,
            "data": asset.model_dump()
        },
        status=201
    )
    