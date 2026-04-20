from fastapi import HTTPException

from src.core.security import hash_password
from src.schemas.base_schema import BaseResponse
from src.schemas.user_schema import UserResponse, UserCreateRequest, UserUpdateRequest
from src.repositories.user_repository import UserRepository


class UserService:
    def __init__(
        self, 
        repo: UserRepository
    ):
        self.repo = repo


    async def get_all_users(
        self
    ) -> BaseResponse[list[UserResponse]]:
        users = await self.repo.get_all_users()
        
        return BaseResponse(
            message="User fetched", 
            data=[UserResponse.model_validate(user) for user in users]
        )


    async def get_user_by_id(
        self, 
        user_id: str
    ) -> BaseResponse[UserResponse]:
        user = await self.repo.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail="User not found"
            )
        
        return BaseResponse(
            message="User fetched", 
            data=UserResponse.model_validate(user)
        )


    async def get_user_by_email(
        self, 
        user_email: str
    ) -> BaseResponse[UserResponse]:
        user = await self.repo.get_user_by_email(user_email)
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail="User not found"
            )
         
        return BaseResponse(
            message="User fetched", 
            data=UserResponse.model_validate(user)
        )


    async def create_user(
        self, 
        request: UserCreateRequest
    ) -> BaseResponse[UserResponse]:
        request.password = hash_password(request.password)
        user = await self.repo.create_user(request)

        return BaseResponse(
            message="User created", 
            data=UserResponse.model_validate(user)
        )


    async def update_user(
        self, 
        user_id: str, 
        request: UserUpdateRequest
    ) -> BaseResponse[UserResponse]:
        if request.password:
            request.password = hash_password(request.password)
        user = await self.repo.update_user(user_id, request)

        if not user:
            raise HTTPException(
                status_code=404, 
                detail="User not found"
            )

        return BaseResponse(
            message="User updated", 
            data=UserResponse.model_validate(user)
        )


    async def delete_user(
        self, 
        user_id: str
    ) -> BaseResponse[None]:
        deleted = await self.repo.delete_user(user_id)

        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="User not found"
            )

        return BaseResponse(
            message="User deleted"
        )