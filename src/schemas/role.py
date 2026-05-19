from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.schemas.validators import RoleName

class RoleRequest(BaseModel):
    name: RoleName

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
