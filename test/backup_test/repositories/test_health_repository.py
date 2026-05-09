from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.health_repository import HealthRepository


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock()
    return redis


@pytest_asyncio.fixture(loop_scope="session")
async def health_repo(db_session: AsyncSession, mock_redis):
    return HealthRepository(db_session, mock_redis)


# ═══════════════════════════════════
# CHECK_DB
# ═══════════════════════════════════

async def test_check_db_executes_without_error(health_repo):
    await health_repo.check_db()


# ═══════════════════════════════════
# CHECK_REDIS
# ═══════════════════════════════════

async def test_check_redis_calls_ping(health_repo, mock_redis):
    await health_repo.check_redis()

    mock_redis.ping.assert_awaited_once()


async def test_check_redis_propagates_error_when_ping_fails(health_repo, mock_redis):
    mock_redis.ping.side_effect = ConnectionError("redis down")

    with pytest.raises(ConnectionError, match="redis down"):
        await health_repo.check_redis()
