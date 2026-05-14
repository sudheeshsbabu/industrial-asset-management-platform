from app.core.protocols import ConfigRepositoryProtocol

class ConfigService:
    """
    Business logic layer for the config domain.

    Depends on ConfigRepositoryProtocol ΓÇö not on any concrete repository class.
    The concrete repository is injected at construction time (Dependency
    Inversion Principle), making this class fully testable without a database.

    Satisfies ConfigServiceProtocol structurally.
    """

    def __init__(self, repo: ConfigRepositoryProtocol):
        self._repo = repo

    async def fetch_all(self) -> list:
        rows = await self._repo.fetch_all()
        return {row['key']: row['value'] for row in rows}

    async def sync_dict(self, data: dict) -> list[str]:
        updated_keys = await self._repo.sync_dict(data)
        return updated_keys