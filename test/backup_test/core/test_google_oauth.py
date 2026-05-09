from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.core.config import settings
from src.core.google_oauth import google_oauth
from src.schemas.oauth_schema import GoogleUserInfo


def make_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def make_mock_client(token_payload: dict, userinfo_payload: dict | None = None) -> MagicMock:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=make_response(token_payload))
    if userinfo_payload is not None:
        client.get = AsyncMock(return_value=make_response(userinfo_payload))
    return client


# ═══════════════════════════════════
# HAPPY PATH
# ═══════════════════════════════════

async def test_google_oauth_returns_user_info_on_success():
    token_payload = {"access_token": "fake-access-token"}
    userinfo_payload = {
        "sub": "google-user-1",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://example.com/p.jpg",
    }

    mock_client = make_mock_client(token_payload, userinfo_payload)

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        result = await google_oauth("auth-code-123")

    assert isinstance(result, GoogleUserInfo)
    assert result.sub == "google-user-1"
    assert result.email == "user@example.com"
    assert result.email_verified is True


async def test_google_oauth_sends_correct_token_request():
    mock_client = make_mock_client(
        {"access_token": "x"},
        {"sub": "1", "email": "a@x.com", "email_verified": True},
    )

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        await google_oauth("auth-code-xyz")

    mock_client.post.assert_awaited_once_with(
        "https://oauth2.googleapis.com/token",
        data={
            "code": "auth-code-xyz",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )


async def test_google_oauth_sends_userinfo_request_with_bearer_token():
    mock_client = make_mock_client(
        {"access_token": "my-token"},
        {"sub": "1", "email": "a@x.com", "email_verified": True},
    )

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        await google_oauth("code")

    mock_client.get.assert_awaited_once_with(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": "Bearer my-token"},
    )


# ═══════════════════════════════════
# ERROR — token endpoint
# ═══════════════════════════════════

async def test_google_oauth_raises_400_with_error_description():
    token_payload = {
        "error": "invalid_grant",
        "error_description": "Bad authorization code",
    }
    mock_client = make_mock_client(token_payload)

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await google_oauth("bad-code")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Bad authorization code"


async def test_google_oauth_raises_400_with_fallback_when_no_description():
    token_payload = {"error": "invalid_grant"}
    mock_client = make_mock_client(token_payload)

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            await google_oauth("bad-code")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid Google code"


async def test_google_oauth_does_not_call_userinfo_when_token_error():
    token_payload = {"error": "invalid_grant"}
    mock_client = make_mock_client(token_payload)

    with patch("src.core.google_oauth.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(HTTPException):
            await google_oauth("bad-code")

    mock_client.get.assert_not_called()
