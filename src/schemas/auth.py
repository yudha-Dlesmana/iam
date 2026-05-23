from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["super_admin@starter.com"])
    password: str = Field(examples=["!Qwer123"])


class SessionResponse(BaseModel):
    device: str
    ip: str
    ua: str
    created_at: datetime
    last_seen: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
