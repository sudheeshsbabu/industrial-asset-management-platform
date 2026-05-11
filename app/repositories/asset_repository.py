async def get_all_assets(conn):
    query = """
        SELECT id, name, site, status
        FROM assets
        ORDER BY id;
    """
    return await conn.fetch(query)

async def get_asset_by_id(conn, asset_id):
    query = """
        SELECT id, name, site, status
        FROM assets
        WHERE id = $1;
    """
    return await conn.fetchrow(query, asset_id)

async def create_asset(conn, data):
    query = """
        INSERT INTO assets (name, site, status)
        VALUES ($1, $2, $3)
        RETURNING id, name, site, status;
    """
    return await conn.fetchrow(
        query,
        data.name,
        data.site,
        data.status
    )