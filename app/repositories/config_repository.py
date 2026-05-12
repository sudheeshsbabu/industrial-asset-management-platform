async def fetch_configs(conn):
    query = """
        SELECT key, value
        FROM app_config
    """

    rows = await conn.fetch(query)

    return {
        row['key']: row['value']
        for row in rows
    }