from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.schemas.validators import RoleName


class RoleCreate(BaseModel):
    name: RoleName

class RoleUpdate(BaseModel):
    name: RoleName | None = None

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
