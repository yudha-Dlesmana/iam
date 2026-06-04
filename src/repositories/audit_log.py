from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.models import AuditLog, User


class AuditLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        action: str | None = None,
        target_type: str | None = None,
        actor_id: str | None = None,
    ) -> list[AuditLog]:
        actor = aliased(User)
        target = aliased(User)
        stmt = (
            select(AuditLog, actor.email, target.email)
            .outerjoin(actor, actor.id == AuditLog.actor_id)
            .outerjoin(
                target,
                (target.id == AuditLog.target_id) & (AuditLog.target_type == "user"),
            )
            .order_by(desc(AuditLog.created_at))
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_type:
            stmt = stmt.where(AuditLog.target_type == target_type)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        rows = []
        for log, actor_email, target_email in result.all():
            log.actor_email = actor_email
            log.target_email = target_email
            rows.append(log)
        return rows

    async def count(
        self,
        action: str | None = None,
        target_type: str | None = None,
        actor_id: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_type:
            stmt = stmt.where(AuditLog.target_type == target_type)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        return await self.session.scalar(stmt) or 0
