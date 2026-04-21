from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from src.schemas.validators import Validators

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, examples=["MyP@ass123"])
    role_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return Validators.password(v)
        

class UserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=8, examples=["MyP@ss123"])
    role_id: int | None = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        return Validators.password(v, optional=True)

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