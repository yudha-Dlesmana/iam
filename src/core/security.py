import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from fastapi import HTTPException
from pydantic import ValidationError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.core.config import settings
from src.schemas.auth_schema import AccessTokenData, RefreshTokenData

_ph = PasswordHasher()

def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False

#internal helpers
def _encode(payload: dict, secret: str) -> str:
    return jwt.encode(
        payload,
        secret, 
        algorithm=settings.JWT_ALGORITHM
    )

def _decode(token: str, secret: str) -> dict:
    try:
        return jwt.decode(
            token,
            key=secret,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# public typed API
def create_access_token(data: AccessTokenData) -> str:
    payload = data.model_dump(mode="json")
    payload["exp"] = int(data.exp.timestamp())
    return _encode(payload, settings.JWT_ACCESS_SECRET)

def create_refresh_token(data: RefreshTokenData) -> str:
    payload = data.model_dump(mode="json")
    payload["exp"] = int(data.exp.timestamp())
    return _encode(payload, settings.JWT_REFRESH_SECRET)

def decode_access_token(token: str) -> AccessTokenData:
    payload = _decode(token, settings.JWT_ACCESS_SECRET)
    try:
        data = AccessTokenData.model_validate(payload)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail="Token payload malformed"
        )
    if data.type != "access":
        raise HTTPException(
            status_code=401, 
            detail="Wrong token type")
    return data

def decode_refresh_token(token: str) -> RefreshTokenData:
    payload = _decode(token, settings.JWT_REFRESH_SECRET)
    try:
        data = RefreshTokenData.model_validate(payload)
    except ValidationError:
        raise HTTPException (
            status_code=422,
            detail="Token payload malformed"
        )
    if data.type != "refresh":
        raise HTTPException (
            status_code=401,
            detail="Wrong token type"
        )
    return data