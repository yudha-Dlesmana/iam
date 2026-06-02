from typing import Literal

from fastapi import APIRouter, Query, status

from src.schemas.role import (
    RoleRequest,
    RolePermissionsRequest,
    RoleResponse,
    RolePermissionsResponse,
)
from src.schemas.common import PaginatedResponse
from src.lib.deps import RoleServiceDep, require_permission
from src.lib.pagination import MAX_PAGE_LIMIT

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "",
    response_model=PaginatedResponse[RoleResponse],
    dependencies=[require_permission("iam.role.read")],
)
async def list_roles(
    service: RoleServiceDep,
    limit: int = Query(default=10, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
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


@router.patch(
    "/{id}/permissions",
    response_model=RolePermissionsResponse,
    dependencies=[require_permission("iam.role.manage")],
)
async def patch_role_permissions(
    id: int,
    data: RolePermissionsRequest,
    service: RoleServiceDep,
    mode: Literal["set", "add"] = Query(default="set"),
):
    if mode == "set":
        return await service.set_permissions(id, data.permission_ids)
    return await service.add_permissions(id, data.permission_ids)


@router.delete(
    "/{id}/permissions/{permission_id}",
    response_model=RolePermissionsResponse,
    dependencies=[require_permission("iam.role.manage")],
)
async def remove_role_permission(id: int, permission_id: int, service: RoleServiceDep):
    return await service.remove_permission(id, permission_id)
