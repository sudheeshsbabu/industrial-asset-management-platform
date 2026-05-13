from app.core.exceptions import NotFoundError

from app.core.protocols import AssetRepositoryProtocol
from app.models.asset import AssetResponse, AssetCreate

class AssetService:
    """
    Business logic layer for the assets domain.

    Depends on AssetRepositoryProtocol ΓÇö not on any concrete repository class.
    The concrete repository is injected at construction time (Dependency
    Inversion Principle), making this class fully testable without a database.

    Satisfies AssetServiceProtocol structurally.
    """

    def __init__(self, repo: AssetRepositoryProtocol):
        self._repo = repo

    async def list_assets(self) -> list[AssetResponse]:
        rows = await self._repo.get_all()
        return [AssetResponse(**dict(row)) for row in rows]

    async def fetch_asset(self, asset_id: int) -> AssetResponse:
        row = await self._repo.get_by_id(asset_id=asset_id)
        if not row:
            raise NotFoundError(f"Asset not found: {asset_id}")
        return AssetResponse(**dict(row))

    async def add_asset(self, data: AssetCreate) -> AssetResponse:
        row = await self._repo.create(data)
        return AssetResponse(**dict(row))