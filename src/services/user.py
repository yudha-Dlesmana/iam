from src.models import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import hash_password
from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.exceptions.base import NotFoundError, ConflictError

class UserService:
    def __init__(self, repo: UserRepository, role_repo: RoleRepository):
        self.repo = repo
        self.role_repo = role_repo
    
    async def _ensure_role(self, role_id: int) -> None:
        if not await self.role_repo.get_by_id(role_id):
            raise NotFoundError(f"role {role_id} not found")
    
    async def get(self, id: str) -> User:
        user = await self.repo.get_by_id(id)
        if not user:
            raise NotFoundError(f"user {id} not found")
        return user

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, email_like: str | None = None
    ) -> tuple[list[User], int]:
        items = await self.repo.get_all(limit, offset, email_like)
        total = await self.repo.count(email_like)
        return items, total
    
    async def create(self, data: UserCreate) -> User:
        if await self.repo.get_by_email(data.email):
            raise ConflictError(f"email '{data.email}' already exists")
        if data.role_id is not None:
            await self._ensure_role(data.role_id)
        user = User(
            email=data.email,
            password=hash_password(data.password),
            role_id=data.role_id
        )
        return await self.repo.save(user)
    
    async def update(self, id: str, data: UserUpdate) -> User:
        user = await self.get(id)
        if data.email and data.email != user.email:
            if await self.repo.get_by_email(data.email):
                raise ConflictError(f"email '{data.email}' already exists")
            user.email = data.email
        if data.password:
            user.password = hash_password(data.password)
        if "role_id" in data.model_fields_set:
            if data.role_id is not None:
                await self._ensure_role(data.role_id)
            user.role_id = data.role_id
        return await self.repo.save(user)

    async def delete(self, id: str) -> None:
        user = await self.get(id)
        await self.repo.delete(user)