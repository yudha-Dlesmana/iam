from typing import Annotated, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from src.schemas.validators import Validators

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user0@example.com"])
    password: str = Field(..., min_length=8, examples=["MyP@ass123"])
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return Validators.password(v)

class AccessTokenData(BaseModel):
    type: Literal["access"] = "access"
    sub: str
    role: int | None 
    exp: datetime

class RefreshTokenData(BaseModel):
    type: Literal["refresh"] = "refresh"
    sub: str
    exp: datetime

TokenData = Annotated[
    AccessTokenData | RefreshTokenData,
    Field(discriminator="type")
]

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"