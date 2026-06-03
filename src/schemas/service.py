from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from src.schemas.permission import PermissionResponse


class ServiceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class ServicePermissionsResponse(ServiceResponse):
    permissions: list[PermissionResponse]
