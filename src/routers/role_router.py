from fastapi import APIRouter, Depends

from src.core.dependency import get_role_service
from src.schemas.base_schema import BaseResponse
from src.schemas.role_schema import RoleResponse, RoleRequest
from src.services.role_services import RoleService


router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get(
    "", 
    status_code=200, 
    response_model=BaseResponse[list[RoleResponse]]
)
async def get_all_roles(
    service: RoleService = Depends(get_role_service)
):
    return await service.get_all_roles()


@router.get(
    "/{role_id}", 
    status_code=200, 
    response_model=BaseResponse[RoleResponse]
)
async def get_role_by_id(
    role_id: int,
    service: RoleService = Depends(get_role_service),
):
    return await service.get_role_by_id(role_id)


@router.get(
    "/name/search",
    status_code=200,
    response_model=BaseResponse[RoleResponse]
)
async def get_role_by_name(
    role_name: str,
    service: RoleService = Depends(get_role_service)
):
    return await service.get_role_by_name(role_name)


@router.post(
    "", 
    status_code=201, 
    response_model=BaseResponse[RoleResponse]
)
async def create_role(
    request: RoleRequest, 
    service: RoleService = Depends(get_role_service)
):
    return await service.create_role(request)


@router.put(
    "/{role_id}", 
    status_code=200, 
    response_model=BaseResponse[RoleResponse]
)
async def update(
    role_id: int,
    request: RoleRequest,
    service: RoleService = Depends(get_role_service)
):
    return await service.update(role_id, request)


@router.delete(
    "/{role_id}", 
    status_code=200, 
    response_model=BaseResponse[RoleResponse]
)
async def delete(
    role_id: int,
    service: RoleService = Depends(get_role_service)
):
    return await service.delete(role_id)