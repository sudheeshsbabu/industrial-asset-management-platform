from app.models.asset import AssetCreate

class PostgresAssetRepository:
    """
    Concrete implementation of AssetRepositoryProtocol backed by asyncpg.
    Receives an asyncpg connection via constructor injection ΓÇö it never
    creates or manages the connection itself (Single Responsibility).
    Satisfies AssetRepositoryProtocol structurally (duck typing / Protocol).
    """
    def __init__(self, conn):
        self.conn = conn

    async def get_all(self) -> list:
        query = """
            SELECT id, name, site, status
            FROM assets
            ORDER BY id;
        """
        return await self.conn.fetch(query)

    async def get_by_id(self, asset_id: int):
        query = """
            SELECT id, name, site, status
            FROM assets
            WHERE id = $1;
        """
        return await self.conn.fetchrow(query, asset_id)

    async def create(self, data: AssetCreate):
        query = """
            INSERT INTO assets (name, site, status)
            VALUES ($1, $2, $3)
            RETURNING id, name, site, status;
        """
        return await self.conn.fetchrow(
            query,
            data.name,
            data.site,
            data.status
        )