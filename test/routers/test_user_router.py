from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app import app
from src.core.dependency import get_user_service
from src.schemas.base_schema import BaseResponse
from src.schemas.user_schema import UserResponse
from src.services.user_service import UserService


def make_user_response(
    user_id: str = "u1",
    email: str = "user@example.com",
    role_id: int | None = None,
) -> UserResponse:
    return UserResponse(
        id=user_id,
        email=email,
        role_id=role_id,
        created_at=datetime.now(),
    )


@pytest.fixture
def mock_service():
    return AsyncMock(spec=UserService)


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_user_service] = lambda: mock_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ═══════════════════════════════════
# GET /user — list
# ═══════════════════════════════════

def test_get_all_users_returns_200_with_list(client, mock_service):
    mock_service.get_all_users.return_value = BaseResponse[list[UserResponse]](
        message="User fetched",
        data=[make_user_response("1", "a@x.com"), make_user_response("2", "b@x.com")],
    )

    response = client.get("/api/v1/user")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User fetched"
    assert len(body["data"]) == 2
    mock_service.get_all_users.assert_awaited_once()


def test_get_all_users_returns_empty_list(client, mock_service):
    mock_service.get_all_users.return_value = BaseResponse[list[UserResponse]](
        message="User fetched",
        data=[],
    )

    response = client.get("/api/v1/user")

    assert response.status_code == 200
    assert response.json()["data"] == []


# ═══════════════════════════════════
# GET /user/{user_id} — by id
# ═══════════════════════════════════

def test_get_user_by_id_returns_200(client, mock_service):
    mock_service.get_user_by_id.return_value = BaseResponse[UserResponse](
        message="User fetched",
        data=make_user_response("u1", "found@x.com"),
    )

    response = client.get("/api/v1/user/u1")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "u1"
    mock_service.get_user_by_id.assert_awaited_once_with("u1")


def test_get_user_by_id_returns_404_when_not_found(client, mock_service):
    mock_service.get_user_by_id.side_effect = HTTPException(
        status_code=404, detail="User not found"
    )

    response = client.get("/api/v1/user/missing")

    assert response.status_code == 404
    assert response.json()["message"] == "User not found"


# ═══════════════════════════════════
# GET /user/email/search — by email
# ═══════════════════════════════════

def test_get_user_by_email_returns_200(client, mock_service):
    mock_service.get_user_by_email.return_value = BaseResponse[UserResponse](
        message="User fetched",
        data=make_user_response(email="search@x.com"),
    )

    response = client.get("/api/v1/user/email/search", params={"user_email": "search@x.com"})

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "search@x.com"
    mock_service.get_user_by_email.assert_awaited_once_with("search@x.com")


def test_get_user_by_email_returns_404_when_not_found(client, mock_service):
    mock_service.get_user_by_email.side_effect = HTTPException(
        status_code=404, detail="User not found"
    )

    response = client.get("/api/v1/user/email/search", params={"user_email": "missing@x.com"})

    assert response.status_code == 404


def test_get_user_by_email_returns_422_when_param_missing(client, mock_service):
    response = client.get("/api/v1/user/email/search")

    assert response.status_code == 422


# ═══════════════════════════════════
# POST /user — create
# ═══════════════════════════════════

def test_create_user_returns_201(client, mock_service):
    mock_service.create_user.return_value = BaseResponse[UserResponse](
        message="User created",
        data=make_user_response(email="new@x.com"),
    )

    response = client.post(
        "/api/v1/user",
        json={"email": "new@x.com", "password": "Newpass1!", "role_id": None},
    )

    assert response.status_code == 201
    assert response.json()["message"] == "User created"
    mock_service.create_user.assert_awaited_once()


def test_create_user_returns_422_when_password_invalid(client, mock_service):
    response = client.post(
        "/api/v1/user",
        json={"email": "new@x.com", "password": "weakpass", "role_id": None},
    )

    assert response.status_code == 422
    mock_service.create_user.assert_not_called()


def test_create_user_returns_422_when_email_invalid(client, mock_service):
    response = client.post(
        "/api/v1/user",
        json={"email": "not-an-email", "password": "Newpass1!", "role_id": None},
    )

    assert response.status_code == 422


def test_create_user_returns_422_when_password_too_short(client, mock_service):
    response = client.post(
        "/api/v1/user",
        json={"email": "x@x.com", "password": "Ab1!", "role_id": None},
    )

    assert response.status_code == 422


# ═══════════════════════════════════
# PUT /user/{user_id} — update
# ═══════════════════════════════════

def test_update_user_returns_200(client, mock_service):
    mock_service.update_user.return_value = BaseResponse[UserResponse](
        message="User updated",
        data=make_user_response("u1"),
    )

    response = client.put(
        "/api/v1/user/u1",
        json={"password": "Newpass1!"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User updated"


def test_update_user_returns_404_when_not_found(client, mock_service):
    mock_service.update_user.side_effect = HTTPException(
        status_code=404, detail="User not found"
    )

    response = client.put(
        "/api/v1/user/missing",
        json={"password": "Newpass1!"},
    )

    assert response.status_code == 404


def test_update_user_returns_422_when_no_field_provided(client, mock_service):
    response = client.put("/api/v1/user/u1", json={})

    assert response.status_code == 422
    mock_service.update_user.assert_not_called()


# ═══════════════════════════════════
# DELETE /user/{user_id}
# ═══════════════════════════════════

def test_delete_user_returns_200(client, mock_service):
    mock_service.delete_user.return_value = BaseResponse[None](
        message="User deleted",
        data=None,
    )

    response = client.delete("/api/v1/user/u1")

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted"
    mock_service.delete_user.assert_awaited_once_with("u1")


def test_delete_user_returns_404_when_not_found(client, mock_service):
    mock_service.delete_user.side_effect = HTTPException(
        status_code=404, detail="User not found"
    )

    response = client.delete("/api/v1/user/missing")

    assert response.status_code == 404
