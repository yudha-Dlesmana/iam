from sqlalchemy.exc import IntegrityError
from src.schemas.permission import PermissionRequest
from src.exceptions.base import ConflictError, NotFoundError, ValidationError
from src.models import Permission
from src.repositories.permission import PermissionRepository
from src.repositories.service import ServiceRepository
from src.lib.db_errors import is_unique_violation, is_fk_violation


class PermissionService:
    def __init__(self, repo: PermissionRepository, service_repo: ServiceRepository):
        self.repo = repo
        self.service_repo = service_repo

    async def get(self, id: int) -> Permission:
        permission = await self.repo.get_by_id(id)
        if not permission:
            raise NotFoundError("permission not found")
        return permission

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> tuple[list[Permission], int]:
        items = await self.repo.get_all(limit, offset, name_like)
        total = await self.repo.count(name_like)
        return items, total

    async def create(self, data: PermissionRequest) -> Permission:
        service = await self.service_repo.get_by_id(data.service_id)
        if not service:
            raise ValidationError("service not found")
        if not data.name.startswith(f"{service.name}."):
            raise ValidationError(f"permission name must start with '{service.name}.'")

        permission = Permission(name=data.name, service_id=data.service_id)
        try:
            return await self.repo.save(permission)
        except IntegrityError as e:
            if is_unique_violation(e):
                raise ConflictError("permission already exists") from e
            if is_fk_violation(e):
                raise ValidationError("service not found") from e
            raise

    async def delete(self, id: int) -> None:
        permission = await self.get(id)
        await self.repo.delete(permission)
