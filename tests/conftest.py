import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from src.app import app
from src.core.config import settings
from src.core.database import get_db
from src.core.redis import get_redis
from src.core.security import hash_password
from src.models import Base, User

test_engine = create_async_engine(settings.TEST_DB_URL, poolclass=NullPool)
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
    # The global rate-limit middleware uses the module-level redis_client singleton
    # directly (not via DI), so point it at the test redis for this test's loop.
    import src.core.rate_limit_middleware as rlm

    original_redis = rlm.redis_client
    rlm.redis_client = redis
    transport = ASGITransport(app=app)
    # Simulate a same-origin browser so the /refresh CSRF guard (_check_origin)
    # accepts the request, just like a real SPA would.
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Sec-Fetch-Site": "same-origin"},
    ) as c:
        yield c
    rlm.redis_client = original_redis
    app.dependency_overrides.clear()


LOGIN = "/v1/auth/login"
REFRESH = "/v1/auth/refresh"
LOGOUT = "/v1/auth/logout"
ALL_LOGOUT = "/v1/auth/all-logout"
SESSIONS = "/v1/auth/sessions"
ME = "/v1/auth/current-user"
CREDENTIALS = {"email": "test@starter.com", "password": "!Qwer123"}


@pytest.fixture
def auth(client):
    class Auth:
        async def post_with_cookie(self, path, token):
            client.cookies.clear()
            client.cookies.set("refresh_token", token, path="/v1/auth")
            return await client.post(path)

        async def login(self):
            return await client.post(LOGIN, json=CREDENTIALS)

        async def refresh(self, token):
            return await self.post_with_cookie(REFRESH, token)

        async def logout(self, token):
            return await self.post_with_cookie(LOGOUT, token)

        async def all_logout(self, token):
            return await self.post_with_cookie(ALL_LOGOUT, token)

        async def sessions(self, access_token):
            return await client.get(
                SESSIONS, headers={"Authorization": f"Bearer {access_token}"}
            )

        async def current_session(self, token, access_token):
            client.cookies.clear()
            client.cookies.set("refresh_token", token, path="/v1/auth")
            return await client.get(
                SESSIONS + "/current",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        async def me(self, access_token):
            return await client.get(
                ME, headers={"Authorization": f"Bearer {access_token}"}
            )

    return Auth()
