import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from src.core.config import settings

async def create_database() -> None:
    base_url = settings.DB_URL.rsplit("/", 1)[0]
    engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT")

    databases= [settings.DB_NAME, settings.TEST_DB_URL]
    async with engine.connect() as connection:
        for db in databases:
            await connection.execute(
                text(f"""
                CREATE DATABASE IF NOT EXISTS `{db}`
                """)
                print(f"✓ {db}")
            )
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_database())