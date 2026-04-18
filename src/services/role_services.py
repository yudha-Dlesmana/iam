from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

from src.schemas.base_schema import BaseResponse
from src.schemas.role_schema import RoleResponse, RoleRequest
from src.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo
    
    async def get_all_roles(self) -> BaseResponse[list[RoleResponse]]:
        try:
            roles = await self.repo.get_all_roles()
            data = [RoleResponse.model_validate(role) for role in roles]
            
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        return BaseResponse(
            message="Role fetched",
            data=data
        )

    async def get_role_by_id(self, role_id: int):
        try:
            role = await self.repo.get_role_by_id(role_id)
        
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return BaseResponse(
            message="Role fetched",
            data=RoleResponse.model_validate(role)
        ) 

    
    async def create_role (self, request: RoleRequest) -> RoleResponse:
        try:
            role = await self.repo.create_role(request)
        
        except IntegrityError as e:
            if e.orig and e.orig.args[0] == 1062:
                raise HTTPException(status_code=409, detail=f"Duplicate value: {e.orig.args[1]}")
            raise HTTPException(status_code=409, detail=f"Conflict: {e.orig.args[1] if e.orig else str(e)}")
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        return BaseResponse(
            message="Role created",
            data=RoleResponse.model_validate(role)
        )

    async def update_role(self, role_id: int, request: RoleRequest) -> RoleResponse:
        try:
            role = await self.repo.update_role(role_id, request)

        except IntegrityError as e:
            if e.orig and e.orig.args[0] == 1062:
                raise HTTPException(status_code=409, detail=f"Duplicate value: {e.orig.args[1]}")
            raise HTTPException(status_code=409, detail=f"Conflict: {e.orig.args[1] if e.orig else str(e)}")
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return BaseResponse(
            message="Role updated",
            data=RoleResponse.model_validate(role)
        )

    async def delete_role(self, role_id: int) -> BaseResponse[None]:
        try:
            deleted = await self.repo.delete_role(role_id)
        
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return BaseResponse( 
            message="Role deleted"
        )