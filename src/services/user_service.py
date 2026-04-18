from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

from src.schemas.base_schema import BaseResponse
from src.schemas.user_schema import UserResponse, UserRequest, UpdatePasswordRequest, UpdateRoleRequest
from src.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_all_users(self) -> BaseResponse[list[UserResponse]]:
        try:
            users = await self.repo.get_all_user()
            data = [UserResponse.model_validate(user) for user in users]
            return BaseResponse(
                message="User fetched",
                data=data
            )

        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

    async def get_user_by_id(self, user_id: str) -> BaseResponse[UserResponse]:
        try:
            user = await self.repo.get_user_by_id(user_id)

        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return BaseResponse(
            message="User fetched",
            data=UserResponse.model_validate(user)
        )
    
    async def get_user_by_email(self, user_email: str) -> BaseResponse[UserResponse]:
        try:
            user = await self.repo.get_user_by_email(user_email)

        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return BaseResponse(
            message="User fetched",
            data=UserResponse.model_validate(user)
        )
    
    async def create_user(self, request: UserRequest) -> BaseResponse[UserResponse]:
        try:
            user = await self.repo.create_user(request)
        
        except IntegrityError as e:
            if e.orig and e.orig.args[0] == 1062:
                raise HTTPException(status_code=409, detail=f"Duplicate value: {e.orig.args[1]}")
            if e.orig and e.orig.args[0] == 1452:
                raise HTTPException(status_code=404, detail=f"Referenced record not found: {e.orig.args[1]}")
            raise HTTPException(status_code=409, detail=f"Conflict: {e.orig.args[1] if e.orig else str(e)}")
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")

        return BaseResponse(
            message="User created",
            data=UserResponse.model_validate(user)
        )

    async def update_role_user(self, user_id: str, request: UpdateRoleRequest) -> BaseResponse[UserResponse]:
        try:
            user = await self.repo.update_user(user_id, request=request)

        except IntegrityError as e:
            raise HTTPException(status_code=404, detail=f"Referenced record not found: {e.orig.args[1]}")
        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return BaseResponse(
            message="User updated",
            data=UserResponse.model_validate(user)
        )
    
    async def update_password_user(self, user_id: str, request: UpdatePasswordRequest) -> BaseResponse[UserResponse]:
        try:
            user = await self.repo.update_user(user_id, request=request)

        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return BaseResponse(
            message="User updated",
            data=UserResponse.model_validate(user)
        )
    
    async def delete_user(self, user_id: str) -> BaseResponse[None]:
        try:
            deleted = self.repo.delete_user(user_id)

        except OperationalError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        
        return BaseResponse(
            message="User deleted"
        )