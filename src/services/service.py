from sqlalchemy.exc import IntegrityError

from src.models import Service
from src.schemas.service import ServiceRequest
from src.repositories.service import ServiceRepository
from src.exceptions.base import ConflictError, NotFoundError
from src.lib.db_errors import is_unique_violation


class ServiceService:
    def __init__(self, repo: ServiceRepository):
        self.repo = repo

    async def get(self, id: int) -> Service:
        service = await self.repo.get_by_id(id)
        if not service:
            raise NotFoundError("service not found")
        return service

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> tuple[list[Service], int]:
        items = await self.repo.get_all(limit, offset, name_like)
        total = await self.repo.count(name_like)
        return items, total

    async def create(self, data: ServiceRequest) -> Service:
        try:
            return await self.repo.save(Service(name=data.name))
        except IntegrityError as e:
            if is_unique_violation(e):
                raise ConflictError("service already exists") from e
            raise

    async def delete(self, id: int) -> None:
        service = await self.get(id)
        await self.repo.delete(service)
