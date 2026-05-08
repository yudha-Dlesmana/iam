import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker

from src.app import app
from src.core.config import settings

@pytest.fixture
def client():
    return TestClient(app)

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine():
    engine = create_async_engine(settings.TEST_DB_URL)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_engine: AsyncEngine):
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        SessionTest = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )
        async with SessionTest() as session:
            yield session

        await trans.rollback()

