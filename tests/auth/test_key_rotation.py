import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from src.core import keys as keys_module
from src.core.config import settings
from src.core.security import create_access_token, decode_access_token
from src.models import Permission, Role, Service, User


def _gen_pem() -> tuple[str, str]:
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub = (
        k.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return priv, pub


def _build_user() -> User:
    role = Role(id=1, name="admin")
    role.permissions = [
        Permission(
            id=1,
            name="iam.user.read",
            service_id=1,
            service=Service(id=1, name="iam"),
        ),
        Permission(
            id=2,
            name="billing.invoice.read",
            service_id=2,
            service=Service(id=2, name="billing"),
        ),
    ]
    return User(id="u1", email="a@b.com", role_id=1, role=role)


@pytest.fixture
def two_kids(monkeypatch, tmp_path):
    for kid in ["iam-key-1", "iam-key-2"]:
        d = tmp_path / kid
        d.mkdir()
        priv, pub = _gen_pem()
        (d / "private.pem").write_text(priv)
        (d / "public.pem").write_text(pub)

    keys_module.reload()
    monkeypatch.setattr(settings, "JWT_KEYS_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "iam-key-1")
    yield
    keys_module.reload()


def test_all_kids_loaded(two_kids):
    pub = keys_module.all_public_keys()
    assert set(pub.keys()) == {"iam-key-1", "iam-key-2"}


def test_active_kid_signs_with_active_key(two_kids):
    token = create_access_token(_build_user())
    header = jwt.get_unverified_header(token)
    assert header["kid"] == "iam-key-1"


def test_old_token_still_verifies_after_active_kid_switch(two_kids, monkeypatch):
    old_token = create_access_token(_build_user())

    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "iam-key-2")
    new_token = create_access_token(_build_user())

    assert jwt.get_unverified_header(old_token)["kid"] == "iam-key-1"
    assert jwt.get_unverified_header(new_token)["kid"] == "iam-key-2"

    old_claims = decode_access_token(old_token)
    new_claims = decode_access_token(new_token)
    assert old_claims["sub"] == "u1"
    assert new_claims["sub"] == "u1"


async def test_consumer_verifies_token_via_jwks(client, two_kids):
    """Simulate a downstream service verifying an IAM-issued token using JWKS."""
    token = create_access_token(_build_user())

    res = await client.get("/.well-known/jwks.json")
    assert res.status_code == 200
    jwks = res.json()["keys"]

    header = jwt.get_unverified_header(token)
    jwk = next(k for k in jwks if k["kid"] == header["kid"])

    public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=settings.JWT_ISSUER,
        audience="billing",
    )
    assert claims["sub"] == "u1"
    assert "billing.invoice.read" in claims["permissions"]


async def test_consumer_rejects_wrong_audience(client, two_kids):
    token = create_access_token(_build_user())

    res = await client.get("/.well-known/jwks.json")
    jwks = res.json()["keys"]
    header = jwt.get_unverified_header(token)
    jwk = next(k for k in jwks if k["kid"] == header["kid"])
    public_key = RSAAlgorithm.from_jwk(json.dumps(jwk))

    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.JWT_ISSUER,
            audience="not-a-service",
        )
