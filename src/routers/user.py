from fastapi import APIRouter, status, Query

from src.schemas.common import PaginatedResponse
from src.schemas.user import UserCreate, UserUpdate, UserResponse
from src.lib.deps import UserServiceDep
from src.lib.deps import require_permission

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    dependencies=[require_permission("iam.user.read")],
)
async def list_user(
    service: UserServiceDep,
    limit: int = 10,
    offset: int = 0,
    email_like: str | None = Query(default=None, min_length=1, max_length=50),
):
    items, total = await service.get_all_paginated(limit, offset, email_like)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("iam.user.create")],
)
async def create_user(data: UserCreate, service: UserServiceDep):
    return await service.create(data)


@router.get(
    "/{id}",
    response_model=UserResponse,
    dependencies=[require_permission("iam.user.read")],
)
async def get_user(id: str, service: UserServiceDep):
    return await service.get(id)


@router.patch(
    "/{id}",
    response_model=UserResponse,
    dependencies=[require_permission("iam.user.update")],
)
async def update_user(id: str, data: UserUpdate, service: UserServiceDep):
    return await service.update(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("iam.user.delete")],
)
async def delete_user(id: str, service: UserServiceDep):
    await service.delete(id)
