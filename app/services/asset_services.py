from app.repositories.asset_repository import (
    get_all_assets, 
    get_asset_by_id,
    create_asset
)

from app.core.exceptions import NotFoundError

async def list_assets(conn):
    return await get_all_assets(conn)

async def fetch_asset(conn, asset_id):
    asset = await get_asset_by_id(conn, asset_id)
    if not asset:
        raise NotFoundError(f'Asset not found: {asset_id}')
    return asset

async def add_asset(conn, data):
    return await create_asset(conn, data)