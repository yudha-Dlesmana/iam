from fastapi import APIRouter, Query, status

from src.schemas.role import (
    RoleRequest,
    RolePermissionsRequest,
    RoleResponse,
    RolePermissionsResponse,
)
from src.schemas.common import PaginatedResponse
from src.lib.deps import RoleServiceDep, require_permission

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "",
    response_model=PaginatedResponse[RoleResponse],
    dependencies=[require_permission("iam.role.read")],
)
async def list_roles(
    service: RoleServiceDep,
    limit: int = 10,
    offset: int = 0,
    name_like: str | None = Query(default=None, min_length=1, max_length=50),
):
    items, total = await service.get_all_paginated(limit, offset, name_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("iam.role.manage")],
)
async def create_role(data: RoleRequest, service: RoleServiceDep):
    return await service.create(data)


@router.get(
    "/{id}",
    response_model=RolePermissionsResponse,
    dependencies=[require_permission("iam.role.read")],
)
async def get_role(id: int, service: RoleServiceDep):
    return await service.get_with_permissions(id)


@router.patch(
    "/{id}",
    response_model=RoleResponse,
    dependencies=[require_permission("iam.role.manage")],
)
async def update_role(id: int, data: RoleRequest, service: RoleServiceDep):
    return await service.update(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("iam.role.manage")],
)
async def delete_role(id: int, service: RoleServiceDep):
    await service.delete(id)


@router.put(
    "/{id}/permissions",
    response_model=RolePermissionsResponse,
    dependencies=[require_permission("iam.role.manage")],
)
async def set_role_permissions(
    id: int, data: RolePermissionsRequest, service: RoleServiceDep
):
    return await service.set_permissions(id, data.permissions_ids)
