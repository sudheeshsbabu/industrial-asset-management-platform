import asyncpg

from app.core.config.config import settings

async def create_db_pool():
    return await asyncpg.create_pool(
        host = settings.DB_HOST,
        port = settings.DB_PORT,
        user = settings.DB_USER,
        password = settings.DB_PASSWORD,
        database = settings.DB_NAME,
        min_size=5,
        max_size=20
    )