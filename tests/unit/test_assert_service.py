"""
Unit tests for AssetService using a FakeAssetRepository.

No database, no HTTP server, no patched imports.
The fake repository is injected directly into AssetService ΓÇö this is
Dependency Injection in action.

Run with:
    uv run pytest tests/unit/test_asset_service.py -v
"""
import pytest

from app.services.asset_services import AssetService
from app.models.asset import AssetCreate, AssetResponse
from app.core.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# Fake repository that satisfies AssetRepositoryProtocol without a DB
# ---------------------------------------------------------------------------

class FakeAssetRepository:
    """
    In-memory asset repository for tests.
    Supports dependency injection into AssetService without any real DB.
    """

    def __init__(self, seed: list[dict] | None = None):
        self._store: dict[int, dict] = {}
        self._next_id: int = 1

        for row in seed or []:
            self._store[row["id"]] = row
            self._next_id = max(self._next_id, row['id'] + 1)

    async def get_all(self, limit: int = 10, offset: int = 0) -> list[dict]:
        return list(self._store.values())
        
    async def get_by_id(self, asset_id: int) -> dict | None:
        return self._store.get(asset_id)

    async def create(self, data: AssetCreate) -> dict:
        new_row = {
            'id': self._next_id,
            'name': data.name,
            'site': data.site,
            'status': data.status
        }
        self._store[self._next_id] = new_row
        self._next_id += 1
        return new_row


# ---------------------------------------------------------------------------
# AssetService test fixtures
# ---------------------------------------------------------------------------

SEED_DATA = [
    {"id": 1, "name": "Robot Arm A", "site": "Factory 1", "status": "active"},
    {"id": 2, "name": "Conveyor B",  "site": "Factory 2", "status": "inactive"},
]

@pytest.fixture
def repo():
    return FakeAssetRepository(SEED_DATA)

@pytest.fixture
def service(repo):
    # Inject DI for fake repository
    return AssetService(repo)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_list_assets_returns_all(service):
    assets = await service.list_assets()
    assert len(assets) == 2
    assert all(isinstance(a, AssetResponse) for a in assets)
    
async def test_fetch_asset_found(service):
    asset = await service.fetch_asset(1)
    assert asset.id == 1
    assert asset.name == "Robot Arm A"
    assert asset.site == "Factory 1"

async def test_fetch_asset_not_found(service):
    with pytest.raises(NotFoundError):
        await service.fetch_asset(999)

async def test_add_asset_returns_response(service):
    data = AssetCreate(name="Drill C", site="Factory 3", status="active")
    created = await service.add_asset(data)
    assert isinstance(created, AssetResponse)
    assert created.name == "Drill C"
    assert created.status == "active"
    assert created.id == 3

async def test_add_asset_persists(service):
    data = AssetCreate(name="Drill C", site="Factory 3", status="active")
    created = await service.add_asset(data)
    retreived = await service.list_assets()
    assert len(retreived) == 3
    
