from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from src.schemas.base_schema import BaseResponse
from src.schemas.role_schema import RoleResponse, RoleRequest
from src.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo
    

    async def get_all(self) -> BaseResponse[list[RoleResponse]]:
        try:
            roles = await self.repo.get_all()
            data = [RoleResponse.model_validate(role) for role in roles]
            return BaseResponse(
                message="Role fetched",
                data=data
            )
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

    async def get_by_id(self, role_id: int):
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

    
    async def create (self, request: RoleRequest) -> RoleResponse:
        try:
            existing = await self.repo.get_role_by_name(request.name)
            if existing:
                raise HTTPException(status_code=400, detail="Role already exists")
            role = await self.repo.create_role(request)
            return BaseResponse(
                message="Role created",
                data=RoleResponse.model_validate(role)
            )
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

    async def update(self, role_id: int, request: RoleRequest) -> RoleResponse:
        try:
            role = await self.repo.update_role(role_id, request)
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return BaseResponse( 
            message="Role updated",
            data=RoleResponse.model_validate(role)
        )

    async def delete(self, role_id: int) -> BaseResponse[None]:
        try:
            deleted = await self.repo.delete_role(role_id)
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found")
        return BaseResponse( 
            message="Role deleted"
        )