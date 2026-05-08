from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core.dependency import (
    get_auth_service,
    get_current_user,
    get_health_service,
    get_oauth_service,
    get_role_service,
    get_user_service,
)
from src.models.user import User
from src.repositories.health_repository import HealthRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth_schema import AccessTokenData, RefreshTokenData
from src.services.auth_service import AuthService
from src.services.health_services import HealthService
from src.services.oauth_service import OAuthService
from src.services.role_services import RoleService
from src.services.user_service import UserService


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.exists = AsyncMock(return_value=False)
    return redis


@pytest.fixture
def access_token_payload():
    return AccessTokenData(
        type="access",
        sub="user-1",
        role=1,
        exp=datetime.now() + timedelta(minutes=30),
    )


@pytest.fixture
def refresh_token_payload():
    return RefreshTokenData(
        type="refresh",
        sub="user-1",
        exp=datetime.now() + timedelta(days=7),
    )


@pytest.fixture
def credentials():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")


# ═══════════════════════════════════
# SERVICE FACTORIES
# ═══════════════════════════════════

def test_get_health_service_returns_health_service(mock_db, mock_redis):
    service = get_health_service(mock_db, mock_redis)

    assert isinstance(service, HealthService)
    assert isinstance(service.repo, HealthRepository)


def test_get_role_service_returns_role_service(mock_db):
    service = get_role_service(mock_db)

    assert isinstance(service, RoleService)
    assert isinstance(service.repo, RoleRepository)


def test_get_user_service_returns_user_service(mock_db):
    service = get_user_service(mock_db)

    assert isinstance(service, UserService)
    assert isinstance(service.repo, UserRepository)


def test_get_auth_service_returns_auth_service(mock_db, mock_redis):
    service = get_auth_service(mock_db, mock_redis)

    assert isinstance(service, AuthService)
    assert isinstance(service.repo, UserRepository)


def test_get_oauth_service_returns_oauth_service(mock_db):
    service = get_oauth_service(mock_db)

    assert isinstance(service, OAuthService)
    assert isinstance(service.oauth_repo, OAuthRepository)
    assert isinstance(service.user_repo, UserRepository)


# ═══════════════════════════════════
# GET_CURRENT_USER — happy path
# ═══════════════════════════════════

async def test_get_current_user_returns_user_when_token_valid(
    mock_db, mock_redis, credentials, access_token_payload
):
    user = User(id="user-1", email="a@x.com", password="x")

    with patch("src.core.dependency.decode_token", return_value=access_token_payload), \
         patch("src.core.dependency.UserRepository") as MockRepo:
        MockRepo.return_value.get_user_by_id = AsyncMock(return_value=user)

        result = await get_current_user(credentials, mock_db, mock_redis)

    assert result is user
    mock_redis.exists.assert_awaited_once_with("blacklist:fake-token")


# ═══════════════════════════════════
# GET_CURRENT_USER — error cases
# ═══════════════════════════════════

async def test_get_current_user_raises_401_when_token_blacklisted(
    mock_db, mock_redis, credentials
):
    mock_redis.exists = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials, mock_db, mock_redis)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token revoked"


async def test_get_current_user_raises_401_when_token_type_not_access(
    mock_db, mock_redis, credentials, refresh_token_payload
):
    with patch("src.core.dependency.decode_token", return_value=refresh_token_payload):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, mock_db, mock_redis)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token type"


async def test_get_current_user_raises_401_when_user_not_found(
    mock_db, mock_redis, credentials, access_token_payload
):
    with patch("src.core.dependency.decode_token", return_value=access_token_payload), \
         patch("src.core.dependency.UserRepository") as MockRepo:
        MockRepo.return_value.get_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, mock_db, mock_redis)

    assert exc.value.status_code == 401
    assert exc.value.detail == "User not found"
