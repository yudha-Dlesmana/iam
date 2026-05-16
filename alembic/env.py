import os
import asyncio
from logging.config import fileConfig
from alembic import context

from sqlalchemy.ext.asyncio import create_async_engine

from src.models.base import Base
from src.core.config import settings


config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

url = os.environ.get("ALEMBIC_DB_URL", settings.DB_URL)


def apply_migration(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        await connection.run_sync(apply_migration)
    await engine.dispose()
    

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
