from sqlalchemy.exc import IntegrityError
from src.models import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import hash_password
from src.repositories.user import UserRepository
from src.lib.db_errors import is_unique_violation, is_fk_violation
from src.exceptions.base import NotFoundError, ConflictError

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    async def get(self, id: str) -> User:
        user = await self.repo.get_by_id(id)
        if not user:
            raise NotFoundError("user not found")
        return user

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, email_like: str | None = None
    ) -> tuple[list[User], int]:
        items = await self.repo.get_all(limit, offset, email_like)
        total = await self.repo.count(email_like)
        return items, total
    
    async def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            password=hash_password(data.password),
            role_id=data.role_id
        )
        try:
            return await self.repo.save(user)
        except IntegrityError as e:
            if is_unique_violation(e):
                raise ConflictError("email already exists")
            if is_fk_violation(e):
                raise NotFoundError("role not found")
            raise
    
    async def update(self, id: str, data: UserUpdate) -> User:
        user = await self.get(id)
        if data.email:
            user.email = data.email
        if data.password:
            user.password = hash_password(data.password)
        if "role_id" in data.model_fields_set:
            user.role_id = data.role_id
        
        try:
            return await self.repo.save(user)
        except IntegrityError as e:
            if is_unique_violation(e):
                raise ConflictError("email already exists")
            if is_fk_violation(e):
                raise NotFoundError("role not found")
            raise

    async def delete(self, id: str) -> None:
        user = await self.get(id)
        await self.repo.delete(user)