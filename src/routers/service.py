from fastapi import APIRouter, Query, status

from src.schemas.service import ServiceRequest, ServiceResponse
from src.schemas.common import PaginatedResponse
from src.lib.deps import ServiceServiceDep, require_permission
from src.lib.pagination import MAX_PAGE_LIMIT

router = APIRouter(prefix="/services", tags=["services"])


@router.get(
    "",
    response_model=PaginatedResponse[ServiceResponse],
    dependencies=[require_permission("iam.service.read")],
)
async def list_services(
    service: ServiceServiceDep,
    limit: int = Query(default=10, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    name_like: str | None = Query(default=None, min_length=1, max_length=50),
):
    items, total = await service.get_all_paginated(limit, offset, name_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("iam.service.manage")],
)
async def create_service(data: ServiceRequest, service: ServiceServiceDep):
    return await service.create(data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("iam.service.manage")],
)
async def delete_service(id: int, service: ServiceServiceDep):
    await service.delete(id)
