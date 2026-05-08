import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as SQLATimeoutError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.database import SessionLocal, engine, get_db


@pytest_asyncio.fixture(loop_scope="session")
async def session_factory(db_engine: AsyncEngine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture(loop_scope="session")
async def tiny_pool_engine():
    eng = create_async_engine(
        settings.TEST_DB_URL,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    )
    yield eng
    await eng.dispose()


# ═══════════════════════════════════
# CONFIG — engine & session
# ═══════════════════════════════════

def test_engine_echo_disabled():
    assert engine.echo is False


def test_engine_pool_configured_correctly():
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10
    assert engine.pool._timeout == 30
    assert engine.pool._recycle == 3600
    assert engine.pool._pre_ping is True


def test_session_info_has_app_metadata():
    session = SessionLocal()

    assert session.info == {"app": "fastapi-starter"}


def test_session_local_expire_on_commit_disabled():
    session = SessionLocal()

    assert session.sync_session.expire_on_commit is False


# ═══════════════════════════════════
# BEHAVIOR — get_db dependency
# ═══════════════════════════════════

async def test_get_db_yields_async_session():
    gen = get_db()
    session = await gen.__anext__()

    assert isinstance(session, AsyncSession)

    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_get_db_closes_session_after_exit():
    gen = get_db()
    session = await gen.__anext__()

    close_calls = []
    original_close = session.close

    async def tracked_close():
        close_calls.append(True)
        await original_close()

    session.close = tracked_close

    await gen.aclose()

    assert close_calls == [True]


# ═══════════════════════════════════
# CONCURRENT SESSIONS
# ═══════════════════════════════════

async def test_multiple_sessions_run_queries_concurrently(session_factory):
    async def run_query(value: int) -> int:
        async with session_factory() as session:
            result = await session.execute(text("SELECT :v"), {"v": value})
            return result.scalar()

    results = await asyncio.gather(*[run_query(i) for i in range(10)])

    assert sorted(results) == list(range(10))


async def test_each_session_has_separate_transaction(session_factory):
    sessions = [session_factory() for _ in range(3)]

    try:
        for session in sessions:
            await session.execute(text("SELECT 1"))

        in_txn = [s.in_transaction() for s in sessions]
        assert all(in_txn)

        identity_ids = {id(s) for s in sessions}
        assert len(identity_ids) == 3
    finally:
        for session in sessions:
            await session.close()


# ═══════════════════════════════════
# POOL — reuse & exhaustion
# ═══════════════════════════════════

async def test_pool_reuses_connection_after_session_close(session_factory):
    async def use_and_close():
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar()

    for _ in range(20):
        assert await use_and_close() == 1


async def test_pool_exhaustion_raises_timeout(tiny_pool_engine):
    factory = async_sessionmaker(tiny_pool_engine, expire_on_commit=False)

    holder = factory()
    await holder.execute(text("SELECT 1"))

    second = factory()
    try:
        with pytest.raises(SQLATimeoutError):
            await second.execute(text("SELECT 1"))
    finally:
        await second.close()
        await holder.close()
