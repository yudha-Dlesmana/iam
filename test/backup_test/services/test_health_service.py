import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import DatabaseError, OperationalError

from src.repositories.health_repository import HealthRepository
from src.services.health_services import DB_TIMEOUT, HealthService, _db_label


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=HealthRepository)


@pytest.fixture
def health_service(mock_repo):
    return HealthService(mock_repo)


# ═══════════════════════════════════
# _DB_LABEL — DB_URL parsing
# ═══════════════════════════════════

@pytest.mark.parametrize("url,expected", [
    ("mysql+aiomysql://user:pass@host/db", "mysql"),
    ("MYSQL://host/db", "mysql"),
    ("postgresql+asyncpg://user@host/db", "postgresql"),
    ("postgres://host/db", "postgresql"),
    ("sqlite:///test.db", "database"),
    ("oracle://host/db", "database"),
])
def test_db_label_from_url(url, expected):
    with patch("src.services.health_services.settings") as mock_settings:
        mock_settings.DB_URL = url

        assert _db_label() == expected


def test_db_label_empty_url_returns_database():
    with patch("src.services.health_services.settings") as mock_settings:
        mock_settings.DB_URL = ""

        assert _db_label() == "database"


def test_db_label_mysql_takes_precedence_over_postgres_in_url():
    with patch("src.services.health_services.settings") as mock_settings:
        mock_settings.DB_URL = "mysql://host/postgres_named_db"

        assert _db_label() == "mysql"


# ═══════════════════════════════════
# CHECK_DATABASE
# ═══════════════════════════════════

async def test_check_database_returns_connected_on_success(health_service, mock_repo):
    mock_repo.check_db = AsyncMock()

    result = await health_service.check_database()

    assert "connected to" in result
    mock_repo.check_db.assert_awaited_once()


async def test_check_database_returns_timeout_message(health_service, mock_repo):
    async def slow_check():
        await asyncio.sleep(DB_TIMEOUT + 1)

    mock_repo.check_db = slow_check

    with patch("src.services.health_services.DB_TIMEOUT", 0.01):
        result = await health_service.check_database()

    assert "timed out" in result
    assert "unavailable" in result


async def test_check_database_returns_operational_error_message(health_service, mock_repo):
    orig = Exception("connection refused")
    mock_repo.check_db = AsyncMock(
        side_effect=OperationalError(statement="...", params={}, orig=orig)
    )

    result = await health_service.check_database()

    assert "unavailable" in result
    assert "connection error" in result
    assert "connection refused" in result


async def test_check_database_returns_database_error_message(health_service, mock_repo):
    orig = Exception("schema mismatch")
    mock_repo.check_db = AsyncMock(
        side_effect=DatabaseError(statement="...", params={}, orig=orig)
    )

    result = await health_service.check_database()

    assert "unavailable" in result
    assert "database error" in result
    assert "schema mismatch" in result


async def test_check_database_includes_db_label_in_message(health_service, mock_repo):
    mock_repo.check_db = AsyncMock()

    with patch("src.services.health_services.settings") as mock_settings:
        mock_settings.DB_URL = "postgresql+asyncpg://host/db"
        result = await health_service.check_database()

    assert "postgresql" in result


async def test_check_database_returns_message_on_unexpected_exception(health_service, mock_repo):
    """EXPECTED: graceful unavailable message. CURRENT BUG: propagates RuntimeError."""
    mock_repo.check_db = AsyncMock(side_effect=RuntimeError("boom"))

    result = await health_service.check_database()

    assert "unavailable" in result
    assert "boom" in result


# ═══════════════════════════════════
# CHECK_REDIS
# ═══════════════════════════════════

async def test_check_redis_returns_connected_on_success(health_service, mock_repo):
    mock_repo.check_redis = AsyncMock()

    result = await health_service.check_redis()

    assert result == "connected"
    mock_repo.check_redis.assert_awaited_once()


async def test_check_redis_returns_timeout_message(health_service, mock_repo):
    async def slow_ping():
        await asyncio.sleep(DB_TIMEOUT + 1)

    mock_repo.check_redis = slow_ping

    with patch("src.services.health_services.DB_TIMEOUT", 0.01):
        result = await health_service.check_redis()

    assert "timed out" in result


async def test_check_redis_returns_error_message_on_exception(health_service, mock_repo):
    mock_repo.check_redis = AsyncMock(side_effect=ConnectionError("redis down"))

    result = await health_service.check_redis()

    assert "redis down" in result


async def test_check_redis_error_message_no_typo(health_service, mock_repo):
    """EXPECTED: 'unavailable'. CURRENT BUG: 'unavailale' (typo)."""
    mock_repo.check_redis = AsyncMock(side_effect=ConnectionError("oops"))

    result = await health_service.check_redis()

    assert "unavailable" in result
    assert "unavailale" not in result


# ═══════════════════════════════════
# CHECK_OTHER_SERVICE
# ═══════════════════════════════════

async def test_check_other_service_returns_ok(health_service):
    result = await health_service.check_other_service()

    assert result == "ok"


async def test_check_other_service_returns_timeout_message(health_service):
    """SERVICE_TIMEOUT < sleep(0.1) duration → forces TimeoutError."""
    with patch("src.services.health_services.SERVICE_TIMEOUT", 0.01):
        result = await health_service.check_other_service()

    assert "timed out" in result
    assert "unavailable" in result


async def test_check_other_service_returns_error_message_on_exception(health_service):
    async def boom(_):
        raise RuntimeError("sleep crashed")

    with patch("src.services.health_services.asyncio.sleep", boom):
        result = await health_service.check_other_service()

    assert "unavailable" in result
    assert "sleep crashed" in result


# ═══════════════════════════════════
# GET_HEALTH — aggregation
# ═══════════════════════════════════

async def test_get_health_returns_aggregated_response(health_service, mock_repo):
    mock_repo.check_db = AsyncMock()
    mock_repo.check_redis = AsyncMock()

    response = await health_service.get_health()

    assert response.message == "Health checked"
    assert response.data.status == "running"
    assert "connected" in response.data.database
    assert response.data.redis == "connected"
    assert response.data.other_service == "ok"


async def test_get_health_includes_failure_messages(health_service, mock_repo):
    db_orig = Exception("db down")
    mock_repo.check_db = AsyncMock(
        side_effect=OperationalError(statement="...", params={}, orig=db_orig)
    )
    mock_repo.check_redis = AsyncMock(side_effect=ConnectionError("redis down"))

    response = await health_service.get_health()

    assert response.data.status == "running"
    assert "unavailable" in response.data.database
    assert "db down" in response.data.database
    assert "redis down" in response.data.redis


async def test_get_health_db_failure_does_not_block_redis_check(health_service, mock_repo):
    """Verify checks run independently — DB failure should not prevent Redis check."""
    mock_repo.check_db = AsyncMock(
        side_effect=OperationalError(statement="...", params={}, orig=Exception("db down"))
    )
    mock_repo.check_redis = AsyncMock()

    response = await health_service.get_health()

    assert "unavailable" in response.data.database
    assert response.data.redis == "connected"
    assert response.data.other_service == "ok"


async def test_get_health_returns_response_when_unexpected_db_exception(health_service, mock_repo):
    """EXPECTED: endpoint never crashes. CURRENT BUG: RuntimeError propagates → 500."""
    mock_repo.check_db = AsyncMock(side_effect=RuntimeError("driver panic"))
    mock_repo.check_redis = AsyncMock()

    response = await health_service.get_health()

    assert response.data.status == "running"
    assert "unavailable" in response.data.database
    assert "driver panic" in response.data.database
    assert response.data.redis == "connected"
