import jwt
import pytest

from src.core.config import settings
from src.core.security import (
    _audience_from,
    create_access_token,
    decode_access_token,
    ACCESS_ALGORITHM,
)
from src.core.keys import active_private_key
from src.models import Permission, Role, Service, User


def _build_user(role_name: str | None, perms: list[str]) -> User:
    if role_name is None:
        return User(id="u1", email="a@b.com", role=None)
    role = Role(id=1, name=role_name)
    role.permissions = [
        Permission(
            id=i + 1, name=p, service_id=1, service=Service(id=1, name=p.split(".")[0])
        )
        for i, p in enumerate(perms)
    ]
    return User(id="u1", email="a@b.com", role_id=1, role=role)


def test_audience_from_no_role():
    u = _build_user(None, [])
    assert _audience_from(u) == [settings.JWT_ISSUER]


def test_audience_from_no_permissions():
    u = _build_user("viewer", [])
    assert _audience_from(u) == [settings.JWT_ISSUER]


def test_audience_from_single_service():
    u = _build_user("admin", ["iam.user.read", "iam.role.manage"])
    assert _audience_from(u) == ["iam"]


def test_audience_from_multiple_services_sorted():
    u = _build_user(
        "admin",
        ["iam.user.read", "billing.invoice.read", "iam.role.manage"],
    )
    assert _audience_from(u) == ["billing", "iam"]


def test_decode_access_token_ok():
    u = _build_user("admin", ["iam.user.read"])
    token = create_access_token(u, sid="test-sid")
    claims = decode_access_token(token)
    assert claims["sub"] == "u1"
    assert claims["iss"] == settings.JWT_ISSUER
    assert claims["role"] == "admin"
    assert claims["permissions"] == ["iam.user.read"]


def test_decode_access_token_rejects_bad_issuer():
    u = _build_user("admin", ["iam.user.read"])
    private_key, kid = active_private_key()
    bad = jwt.encode(
        {
            "sub": u.id,
            "iss": "evil-iss",
            "aud": settings.JWT_ISSUER,
            "permissions": [],
            "role": "admin",
            "email": u.email,
            "jti": "x",
        },
        private_key,
        algorithm=ACCESS_ALGORITHM,
        headers={"kid": kid},
    )
    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(bad)


def test_decode_access_token_rejects_bad_audience():
    u = _build_user("admin", ["iam.user.read"])
    private_key, kid = active_private_key()
    bad = jwt.encode(
        {
            "sub": u.id,
            "iss": settings.JWT_ISSUER,
            "aud": "not-iam",
            "permissions": [],
            "role": "admin",
            "email": u.email,
            "jti": "x",
        },
        private_key,
        algorithm=ACCESS_ALGORITHM,
        headers={"kid": kid},
    )
    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(bad)


def test_decode_access_token_rejects_missing_kid():
    u = _build_user("admin", ["iam.user.read"])
    private_key, _ = active_private_key()
    bad = jwt.encode(
        {
            "sub": u.id,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_ISSUER,
            "permissions": [],
            "role": "admin",
            "email": u.email,
            "jti": "x",
        },
        private_key,
        algorithm=ACCESS_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(bad)


def test_decode_access_token_rejects_unknown_kid():
    u = _build_user("admin", ["iam.user.read"])
    private_key, _ = active_private_key()
    bad = jwt.encode(
        {
            "sub": u.id,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_ISSUER,
            "permissions": [],
            "role": "admin",
            "email": u.email,
            "jti": "x",
        },
        private_key,
        algorithm=ACCESS_ALGORITHM,
        headers={"kid": "nonexistent-kid"},
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(bad)
