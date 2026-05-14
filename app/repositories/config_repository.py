class PostgresConfigRepository:
    def __init__(self, conn):
        self.conn = conn
    async def fetch_all(self) -> list:
        """Fetch all config entries from the DB as a key-value dict."""

        query = """
            SELECT key, value
            FROM app_config
        """

        return await self.conn.fetch(query)

    async def upsert(self, key: str, value: str) -> bool:
        """
        Insert or update a single config entry only if the value has changed.
        Uses a conditional ON CONFLICT clause so no write is performed when the
        stored value already matches ΓÇö preventing duplicate/redundant updates.

        Returns True if a row was inserted or updated, False if no change was needed.
        """
        query = """
            INSERT INTO app_config (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value,
                updated_at = NOW()
            WHERE app_config.value != EXCLUDED.value
            RETURNING key
        """
        return await self.conn.fetchrow(query, key, value)

    async def sync_dict(self, env_dict: dict) -> list[str]:
        """
        Sync a flat key-value dict (e.g. from Settings.model_dump()) to the DB.
        Only inserts or updates entries whose value differs from what is stored.
        Duplicate / unchanged values are silently skipped.

        Returns a list of keys that were actually inserted or updated.
        """
        updated_keys = []
        for key, value in env_dict.items():
            was_updated = await self.upsert(key, str(value))
            if was_updated:
                updated_keys.append(key)
        return updated_keys