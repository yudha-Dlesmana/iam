from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr, model_validator

from src.schemas.validators import StrongPassword

class UserCreate(BaseModel):
    email: EmailStr = Field(examples=["super_admin@starter.com"])
    password: StrongPassword = Field(examples=["!Qwer123"])
    role_id: int | None = Field(default=None, gt=0, examples=[1])

class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, examples=["super_admin@starter.com"])
    password: StrongPassword | None = Field(default=None, examples=['!Qwer123'])
    role_id: int | None = Field(default=None, gt=0, examples=[2])

    @model_validator(mode="after")
    def at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role_name: str | None
    created_at: datetime
    updated_at: datetime
