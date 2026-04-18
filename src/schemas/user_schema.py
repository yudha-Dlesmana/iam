from typing import Annotated, Literal, Union
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

class UserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            raise ValueError("password must contain symbol")
        return v

class UpdateRoleRequest(BaseModel):
    role_id: int

class UpdatePasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            raise ValueError("password must contain symbol")
        return v

UserUpdateRequest = Union[UpdateRoleRequest, UpdatePasswordRequest]

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    password: str               # temp
    role_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}