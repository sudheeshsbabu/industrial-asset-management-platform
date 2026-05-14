from aiohttp import web

from app.models.pagination import PaginatedResponse
from app.models.asset import AssetCreate, AssetResponse

async def get_assets(request):
    try:
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 10))
    except ValueError:
        page = 1
        page_size = 10

    if page < 1: page = 1
    if page_size < 1: page_size = 10

    offset = (page - 1) * page_size

    async with request.app['db'].acquire() as conn:
        service = request.app["asset_service_factory"](conn)
        assets = await service.list_assets(limit=page_size, offset=offset)
        total_count = await service.count_assets()
    
    response_data = PaginatedResponse[AssetResponse].build_paginated_response(
        results=assets,
        total_count=total_count,
        page=page,
        page_size=page_size,
        url=request.url
    )
    return web.json_response(response_data.model_dump())

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
    