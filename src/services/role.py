from sqlalchemy.exc import IntegrityError
from src.models import Role
from src.schemas.role import RoleRequest
from src.repositories.role import RoleRepository
from src.exceptions.base import NotFoundError, ConflictError, ValidationError
from src.lib.db_errors import is_check_violation, is_unique_violation


class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo

    @staticmethod
    def _save_error(e: IntegrityError) -> Exception:
        if is_unique_violation(e):
            return ConflictError("role already exists")
        if is_check_violation(e, "role_name_no_whitespace"):
            return ValidationError("role must not contain whitespace")
        return e

    async def get(self, id: int) -> Role:
        role = await self.repo.get_by_id(id)
        if not role:
            raise NotFoundError("role not found")
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
        except IntegrityError as e:
            raise self._save_error(e) from e

    async def update(self, id: int, data: RoleRequest) -> Role:
        role = await self.get(id)
        role.name = data.name

        try:
            return await self.repo.save(role)
        except IntegrityError as e:
            raise self._save_error(e) from e

    async def delete(self, id: int) -> None:
        role = await self.get(id)

        try:
            await self.repo.delete(role)
        except IntegrityError:
            raise ConflictError("role still referenced by users")
