from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["super_admin@starter.com"])
    password: str = Field(examples=["!Qwer123"])


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
