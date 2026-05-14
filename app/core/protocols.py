from typing import Protocol, runtime_checkable

from app.models.asset import AssetCreate, AssetResponse

@runtime_checkable
class AssetRepositoryProtocol(Protocol):
    """
    Defines the data-access contract for the assets domain.

    Any concrete class that implements these methods (Postgres, in-memory fake, etc.)
    satisfies this protocol without needing to inherit from it.
    """

    async def get_all(self):
        ...

    async def get_by_id(self, asset_id: int):
        ...

    async def create(self, data: AssetCreate):
        ...


@runtime_checkable
class AssetServiceProtocol(Protocol):
    """
    Defines the business-logic contract for the assets domain.

    Handlers depend only on this interface - they never import a concrete
    service class.
    """

    async def list_assets(self) -> list[AssetResponse]:
        ...

    async def fetch_asset(self, asset_id: int) -> AssetResponse:
        ...

    async def add_asset(self, data: AssetCreate) -> AssetResponse:
        ...

@runtime_checkable
class ConfigRefreshStrategy(Protocol):
    async def run(self, app) -> None:
        ...

@runtime_checkable
class ConfigRepositoryProtocol(Protocol):
    async def fetch_all(self): ...
    async def sync_dict(self, env_dict: dict) -> list[str]: ...

@runtime_checkable
class ConfigServiceProtocol(Protocol):
    """
    Defines the business-logic contract for the config domain.

    Handlers depend only on this interface - they never import a concrete
    service class.
    """

    async def fetch_all(self) -> dict[str, str]:
        ...

    async def sync_dict(self, data: dict) -> list[str]:
        ...