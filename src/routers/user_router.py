from src.schemas.user_schema import UpdatePasswordRequest
from src.schemas.user_schema import UpdateRoleRequest
from fastapi import APIRouter, Depends

from src.core.dependency import get_user_service
from src.schemas.base_schema import BaseResponse
from src.schemas.user_schema import UserResponse, UserRequest, UserUpdateRequest
from src.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["Users"])

@router.get(
    "", 
    status_code=200, 
    response_model=BaseResponse[list[UserResponse]]
)
async def get_all_users(
    service: UserService = Depends(get_user_service)
):
    return await service.get_all_users()

@router.get(
    "/{user_id}", 
    status_code=200,
    response_model=BaseResponse[UserResponse]
)
async def get_user_by_user_id(
    user_id: str,
    service: UserService = Depends(get_user_service)
):
    return await service.get_user_by_id(user_id)

@router.get(
    "/email/search",
    status_code=200,
    response_model=BaseResponse[UserResponse]
)
async def get_user_by_email(
    user_email: str,
    service: UserService = Depends(get_user_service)
):
    return await service.get_user_by_email(user_email)

@router.post(
    "",
    status_code=201,
    response_model=BaseResponse[UserResponse]
)
async def create_user(
    request: UserRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(request)

@router.put(
    "/{user_id}/role",
    status_code=200,
    response_model=BaseResponse[UserResponse]
)
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.update_role_user(user_id, request)

@router.put(
    "/{user_id}/password",
    status_code=200,
    response_model=BaseResponse[UserResponse]
)
async def update_user_password(
    user_id: str,
    request: UpdatePasswordRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.update_password_user(user_id, request)

@router.delete(
    "/{user_id}",
    status_code=200,
    response_model=BaseResponse[None]
)
async def delete_user(
    user_id: str,
    service:UserService = Depends(get_user_service)
):
    return await service.delete_user(user_id)