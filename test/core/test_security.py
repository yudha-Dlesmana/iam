import pytest
from src.core.config import settings
import pytest
from fastapi import HTTPException
from jose import jwt
from datetime import datetime, timedelta, timezone
from src.core.security import hash_password, verify_password, create_token, decode_token
from src.schemas.auth_schema import AccessTokenData

def test_verify_password_return_true_for_correct_password():
    plain = "!Qwer123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True

def test_verify_password_return_false_for_not_correct_password():
    plain = "!Qwer123"
    wrong_password = "!qwer321"
    hashed = hash_password(plain)
    assert verify_password(wrong_password, hashed) is False

def test_hash_password_produces_different_hashes():
    h1 = hash_password("!Qwer123")
    h2 = hash_password("!Qwer123")
    assert h1 != h2

def test_token_roundtrip():
    data = AccessTokenData(
        sub="user-123",
        role=1,
        exp=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    token = create_token(data)
    decode = decode_token(token)
    assert decode.sub == "user-123"
    assert decode.role == 1
    assert decode.type == "access"

def test_decode_token_raises_when_expired():
    data= AccessTokenData(
        sub="user-123",
        role=1,
        exp=datetime.now(timezone.utc) -timedelta(minutes=1)
    )
    token = create_token(data)

    with pytest.raises(HTTPException) as exc:
        decode_token(token)
    
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has expired"

def test_decode_token_raise_invalid_token_for_fake_token():
    fake_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImlhdCI6MTY3Mjc2NjAyOCwiZXhwIjoxNjc0NDk0MDI4fQ.kCak9sLJr74frSRVQp0_27BY4iBCgQSmoT3vQVWKzJg"
    with pytest.raises(HTTPException) as exc:
        decode_token(fake_token)
    
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"

def test_decode_token_raises_when_payload_malformed():
    bad_payload = {"foo": "bar"}
    token = jwt.encode(
        bad_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    with pytest.raises(HTTPException) as exc:
        decode_token(token)
    
    assert exc.value.status_code == 422
    assert exc.value.detail == "Token payload malformed" 