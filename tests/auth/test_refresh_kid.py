import jwt

from src.core.security import create_refresh_token, decode_refresh_token
from src.core.config import settings


def test_refresh_token_has_kid():
    token, _, _ = create_refresh_token("user-1")
    assert jwt.get_unverified_header(token)["kid"] == settings.JWT_REFRESH_ACTIVE_KID


def test_decode_active_kid_ok():
    token, _, _ = create_refresh_token("user-1")
    assert decode_refresh_token(token)["sub"] == "user-1"


def test_old_kid_active_kid_ok(monkeypatch):
    monkeypatch.setitem(settings.JWT_REFRESH_SECRETS, "v2", "secret-v2")

    token, _, _ = create_refresh_token("user-1")
    monkeypatch.setattr(settings, "JWT_REFRESH_ACTIVE_KID", "v2")
    assert decode_refresh_token(token)["sub"] == "user-1"
