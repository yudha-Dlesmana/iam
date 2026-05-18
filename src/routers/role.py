from src.schemas.common import PaginatedResponse
from fastapi import APIRouter, Query, status

from src.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from src.lib.deps import RoleServiceDep

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("", response_model=PaginatedResponse[RoleResponse])
async def list_roles(
    service: RoleServiceDep,
    limit: int = 10,
    offset: int = 0,
    name_like: str | None = Query(default=None, min_length=1, max_length=50)
):
    items, total = await service.get_all_paginated(limit, offset, name_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(data: RoleCreate, service: RoleServiceDep):
    return await service.create(data)

@router.get("/{id}", response_model=RoleResponse)
async def get_role(id: int, service: RoleServiceDep):
    return await service.get(id)

@router.patch("/{id}", response_model=RoleResponse)
async def update_role(id: int, data: RoleUpdate, service: RoleServiceDep):
    return await service.update(id, data)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(id: int, service: RoleServiceDep):
    await service.delete(id)