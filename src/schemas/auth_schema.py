from botocore import config
from fastapi.openapi.models import Example
from fastapi import Form, HTTPException
from typing import Annotated, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user0@example.com"])
    password: str = Field(..., min_length=8, examples=["MyP@ass123"])

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