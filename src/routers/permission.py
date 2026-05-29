from fastapi import APIRouter, Query

from src.schemas.permission import PermissionResponse
from src.schemas.common import PaginatedResponse
from src.lib.deps import PermissionServiceDep
from src.lib.deps import require_role

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
    dependencies=[require_role("super_admin")],
)


@router.get("", response_model=PaginatedResponse[PermissionResponse])
async def list_permissions(
    service: PermissionServiceDep,
    limit: int = 10,
    offset: int = 0,
    name_like: str | None = Query(default=None, min_length=1, max_length=100),
):
    items, total = await service.get_all_paginated(limit, offset, name_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
