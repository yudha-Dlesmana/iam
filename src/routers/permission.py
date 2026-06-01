from fastapi import APIRouter, Query, status

from src.schemas.permission import PermissionRequest, PermissionResponse
from src.schemas.common import PaginatedResponse
from src.lib.deps import PermissionServiceDep, require_permission
from src.lib.pagination import MAX_PAGE_LIMIT

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
)


@router.get(
    "",
    response_model=PaginatedResponse[PermissionResponse],
    dependencies=[require_permission("iam.permission.read")],
)
async def list_permissions(
    service: PermissionServiceDep,
    limit: int = Query(default=10, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    name_like: str | None = Query(default=None, min_length=1, max_length=100),
):
    items, total = await service.get_all_paginated(limit, offset, name_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("iam.permission.manage")],
)
async def create_permission(data: PermissionRequest, service: PermissionServiceDep):
    return await service.create(data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("iam.permission.manage")],
)
async def delete_permission(id: int, service: PermissionServiceDep):
    await service.delete(id)
