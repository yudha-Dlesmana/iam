from src.models import Permission
from src.repositories.permission import PermissionRepository


class PermissionService:
    def __init__(self, repo: PermissionRepository):
        self.repo = repo

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> tuple[list[Permission], int]:
        items = await self.repo.get_all(limit, offset, name_like)
        total = await self.repo.count(name_like)
        return items, total
