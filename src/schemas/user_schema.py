from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import datetime

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, examples=["MyP@ass123"])
    role_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v)
        if not (has_letter and has_digit and has_symbol):
            raise ValueError("Password must contain letter, number and symbol")
        return v

class UserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=8, examples=["MyP@ss123"])
    role_id: int | None = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v)
        if not(has_letter and has_digit and has_symbol):
            raise ValueError("password must contain symbol")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UserUpdateRequest":
        if self.password is None and self.role_id is None:
            raise ValueError("At least one field (password or role_id) must be provided")
        return self

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}