from sqlalchemy.exc import IntegrityError
from src.models import Role
from src.schemas.role import RoleRequest
from src.repositories.role import RoleRepository
from src.exceptions.base import NotFoundError, ConflictError

class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo

    async def get(self, id: int) -> Role:
        role = await self.repo.get_by_id(id)
        if not role:
            raise NotFoundError(f"role not found")
        return role

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> tuple[list[Role], int]:
        items = await self.repo.get_all(limit, offset, name_like)
        total = await self.repo.count(name_like)
        return items, total

    async def create(self, data: RoleRequest) -> Role:
        try:
            return await self.repo.save(Role(name=data.name))
        except IntegrityError:
            raise ConflictError(f"{data.name} already exists or invalid")

    async def update(self, id: int, data: RoleRequest) -> Role:
        role = await self.get(id)
        role.name = data.name

        try:
            return await self.repo.save(role)
        except IntegrityError:
            raise ConflictError(f"{data.name} already exists or invalid")

    async def delete(self, id: int) -> None:
        role = await self.get(id)
        
        try:
            await self.repo.delete(role)
        except IntegrityError:
            raise ConflictError("role still referenced by users")