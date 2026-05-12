from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError

from src.core.config import settings
from src.schemas.auth_schema import TokenData


_ph = PasswordHasher()
_token_adapter = TypeAdapter(TokenData)

def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def create_token(data: TokenData) -> str:
    payload = data.model_dump(mode="json")
    payload["exp"] = int(data.exp.timestamp())

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )

def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return _token_adapter.validate_python(payload)
        
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
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail="Token payload malformed"
        )