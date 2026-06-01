from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.schemas.validators import RoleName
from src.schemas.permission import PermissionResponse


class RoleRequest(BaseModel):
    name: RoleName


class RolePermissionsRequest(BaseModel):
    permission_ids: list[int]


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    single_session: bool
    created_at: datetime
    updated_at: datetime


class RolePermissionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    single_session: bool
    permissions: list["PermissionResponse"]
