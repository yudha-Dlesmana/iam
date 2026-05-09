from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.user_schema import UserCreateRequest, UserUpdateRequest
from src.services.user_service import UserService


def make_user(
    user_id: str = "user-1",
    email: str = "test@starter.com",
    password: str = "hashed",
    role_id: int | None = None,
) -> User:
    return User(
        id=user_id,
        email=email,
        password=password,
        role_id=role_id,
        created_at=datetime.now(),
    )


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def user_service(mock_repo):
    return UserService(mock_repo)


# ═══════════════════════════════════
# GET_ALL_USERS
# ═══════════════════════════════════

async def test_get_all_users_returns_response_with_user_list(user_service, mock_repo):
    mock_repo.get_all_users.return_value = [
        make_user(user_id="1", email="a@starter.com"),
        make_user(user_id="2", email="b@starter.com"),
    ]

    result = await user_service.get_all_users()

    assert result.message == "User fetched"
    assert len(result.data) == 2
    assert result.data[0].email == "a@starter.com"
    mock_repo.get_all_users.assert_awaited_once()


async def test_get_all_users_returns_empty_list_when_no_users(user_service, mock_repo):
    mock_repo.get_all_users.return_value = []

    result = await user_service.get_all_users()

    assert result.data == []


# ═══════════════════════════════════
# GET_USER_BY_ID
# ═══════════════════════════════════

async def test_get_user_by_id_returns_user_response(user_service, mock_repo):
    mock_repo.get_user_by_id.return_value = make_user(user_id="abc", email="found@starter.com")

    result = await user_service.get_user_by_id("abc")

    assert result.message == "User fetched"
    assert result.data.id == "abc"
    assert result.data.email == "found@starter.com"
    mock_repo.get_user_by_id.assert_awaited_once_with("abc")


async def test_get_user_by_id_raises_404_when_not_found(user_service, mock_repo):
    mock_repo.get_user_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await user_service.get_user_by_id("missing")

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


# ═══════════════════════════════════
# GET_USER_BY_EMAIL
# ═══════════════════════════════════

async def test_get_user_by_email_returns_user_response(user_service, mock_repo):
    mock_repo.get_user_by_email.return_value = make_user(email="search@starter.com")

    result = await user_service.get_user_by_email("search@starter.com")

    assert result.data.email == "search@starter.com"
    mock_repo.get_user_by_email.assert_awaited_once_with("search@starter.com")


async def test_get_user_by_email_raises_404_when_not_found(user_service, mock_repo):
    mock_repo.get_user_by_email.return_value = None

    with pytest.raises(HTTPException) as exc:
        await user_service.get_user_by_email("missing@starter.com")

    assert exc.value.status_code == 404


# ═══════════════════════════════════
# CREATE_USER
# ═══════════════════════════════════

async def test_create_user_hashes_password_and_calls_repo(user_service, mock_repo):
    created = make_user(email="new@starter.com")
    mock_repo.create_user.return_value = created

    request = UserCreateRequest(
        email="new@starter.com",
        password="Plain1234!",
        role_id=None,
    )

    with patch("src.services.user_service.hash_password", return_value="hashed-pwd") as mock_hash:
        result = await user_service.create_user(request)

    mock_hash.assert_called_once_with("Plain1234!")
    assert request.password == "hashed-pwd"
    mock_repo.create_user.assert_awaited_once_with(request)
    assert result.message == "User created"
    assert result.data.email == "new@starter.com"


# ═══════════════════════════════════
# UPDATE_USER
# ═══════════════════════════════════

async def test_update_user_hashes_password_when_provided(user_service, mock_repo):
    mock_repo.update_user.return_value = make_user(user_id="u1")
    request = UserUpdateRequest(password="Newpass1!")

    with patch("src.services.user_service.hash_password", return_value="hashed-new") as mock_hash:
        result = await user_service.update_user("u1", request)

    mock_hash.assert_called_once_with("Newpass1!")
    assert request.password == "hashed-new"
    mock_repo.update_user.assert_awaited_once_with("u1", request)
    assert result.message == "User updated"


async def test_update_user_skips_hashing_when_password_none(user_service, mock_repo):
    mock_repo.update_user.return_value = make_user(user_id="u1")
    request = UserUpdateRequest(role_id=2)

    with patch("src.services.user_service.hash_password") as mock_hash:
        await user_service.update_user("u1", request)

    mock_hash.assert_not_called()
    mock_repo.update_user.assert_awaited_once_with("u1", request)


async def test_update_user_raises_404_when_not_found(user_service, mock_repo):
    mock_repo.update_user.return_value = None
    request = UserUpdateRequest(role_id=2)

    with pytest.raises(HTTPException) as exc:
        await user_service.update_user("missing", request)

    assert exc.value.status_code == 404


# ═══════════════════════════════════
# DELETE_USER
# ═══════════════════════════════════

async def test_delete_user_returns_response_when_deleted(user_service, mock_repo):
    mock_repo.delete_user.return_value = True

    result = await user_service.delete_user("u1")

    assert result.message == "User deleted"
    assert result.data is None
    mock_repo.delete_user.assert_awaited_once_with("u1")


async def test_delete_user_raises_404_when_not_found(user_service, mock_repo):
    mock_repo.delete_user.return_value = False

    with pytest.raises(HTTPException) as exc:
        await user_service.delete_user("missing")

    assert exc.value.status_code == 404
