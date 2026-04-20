from fastapi import HTTPException

from src.schemas.base_schema import BaseResponse
from src.schemas.role_schema import RoleResponse, RoleRequest
from src.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(
        self, 
        repo: RoleRepository
    ):
        self.repo = repo
    
    async def get_all_roles(
        self
    ) -> BaseResponse[list[RoleResponse]]:
        roles = await self.repo.get_all_roles()
        
        return BaseResponse(
            message="Role fetched",
            data=[RoleResponse.model_validate(role) for role in roles]
        )

    async def get_role_by_id(
        self, 
        role_id: int
    ) -> BaseResponse[RoleResponse]:
        role = await self.repo.get_role_by_id(role_id)
        
        if not role:
            raise HTTPException(
                status_code=404, 
                detail="Role not found"
            )
        
        return BaseResponse(
            message="Role fetched",
            data=RoleResponse.model_validate(role)
        ) 

    async def get_role_by_name(
        self,
        role_name: str
    ) -> BaseResponse[RoleResponse]:
        role = await self.repo.get_role_by_name(role_name)

        if not role:
            raise HTTPException(
                status_code=404,
                detail="Role not found"
            )

        return BaseResponse(
            message="Role fetched",
            data=RoleResponse.model_validate(role)
        )
    
    async def create_role (
        self, 
        request: RoleRequest
    ) -> RoleResponse:
        role = await self.repo.create_role(request)
        
        return BaseResponse(
            message="Role created",
            data=RoleResponse.model_validate(role)
        )

    async def update_role(
        self, 
        role_id: int, 
        request: RoleRequest
    ) -> RoleResponse:
        role = await self.repo.update_role(role_id, request)

        if not role:
            raise HTTPException(
                status_code=404, 
                detail="Role not found"
            )
        
        return BaseResponse(
            message="Role updated",
            data=RoleResponse.model_validate(role)
        )

    async def delete_role(
        self, 
        role_id: int
    ) -> BaseResponse[None]:
        deleted = await self.repo.delete_role(role_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="Role not found"
            )
        
        return BaseResponse( 
            message="Role deleted"
        )