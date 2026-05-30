from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PermissionRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    service_id: int


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
