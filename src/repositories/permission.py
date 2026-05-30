from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Permission


class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Permission:
        return await self.session.get(Permission, id)

    async def get_by_ids(self, ids: list[int]) -> list[Permission]:
        if not ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(ids))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_all(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.id)
        if name_like:
            stmt = stmt.where(Permission.name.ilike(f"%{name_like}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self, name_like: str | None = None) -> int:
        stmt = select(func.count()).select_from(Permission)
        if name_like:
            stmt = stmt.where(Permission.name.ilike(f"%{name_like}%"))
        return await self.session.scalar(stmt) or 0

    async def save(self, permission: Permission) -> Permission:
        self.session.add(permission)
        await self.session.flush()
        await self.session.refresh(permission)
        return permission

    async def delete(self, permission: Permission) -> None:
        await self.session.delete(permission)
        await self.session.flush()
