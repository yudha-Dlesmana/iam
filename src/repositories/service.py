from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Service


class ServiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Service:
        return await self.session.get(Service, id)

    async def get_all(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> list[Service]:
        stmt = select(Service).order_by(Service.id)
        if name_like:
            stmt = stmt.where(Service.name.ilike(f"%{name_like}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self, name_like: str | None = None) -> int:
        stmt = select(func.count()).select_from(Service)
        if name_like:
            stmt = stmt.where(Service.name.ilike(f"%{name_like}%"))
        return await self.session.scalar(stmt) or 0

    async def save(self, service: Service) -> Service:
        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)
        return service

    async def delete(self, service: Service) -> None:
        await self.session.delete(service)
        await self.session.flush()
