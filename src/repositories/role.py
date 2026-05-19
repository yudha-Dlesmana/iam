from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Role

class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Role | None:
        return await self.session.get(Role, id)
    
    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return await self.session.scalar(stmt)
    
    async def get_all(
        self, 
        limit: int = 10, 
        offset: int = 0,
        name_like: str | None = None
    ) -> list[Role]:
        stmt = select(Role).order_by(Role.id)
        if name_like:
            stmt = stmt.where(Role.name.ilike(f"%{name_like}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self, name_like: str | None = None) -> int:
        stmt = select(func.count()).select_from(Role)
        if name_like:
            stmt = stmt.where(Role.name.ilike(f"%{name_like}%"))
        return await self.session.scalar(stmt) or 0

    async def save(self, role: Role) -> Role:    
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role
    
    async def delete(self, role: Role) -> None:
        await self.session.delete(role)
        await self.session.flush()
    