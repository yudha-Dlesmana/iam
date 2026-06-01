from src.models import AuditLog
from src.repositories.audit_log import AuditLogRepository


class AuditLogService:
    def __init__(self, repo: AuditLogRepository):
        self.repo = repo

    async def get_all_paginated(
        self,
        limit: int = 10,
        offset: int = 0,
        action: str | None = None,
        target_type: str | None = None,
        actor_id: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        items = await self.repo.get_all(limit, offset, action, target_type, actor_id)
        total = await self.repo.count(action, target_type, actor_id)
        return items, total
