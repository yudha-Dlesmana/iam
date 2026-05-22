import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.app import app
from src.core.config import settings
from src.core.database import get_db
from src.core.redis import get_redis
from src.core.security import hash_password
from src.models import Base, User

test_engine = create_async_engine(settings.TEST_DB_URL)
TestSession = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture
async def db():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def redis():
    r = from_url(settings.REDIS_URL, db=15, decode_responses=True)
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()


@pytest_asyncio.fixture
async def user(db):
    u = User(email="test@starter.com", password=hash_password("!Qwer123"))
    db.add(u)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def client(db, redis):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
