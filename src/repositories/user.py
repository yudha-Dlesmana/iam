from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: str) -> User | None:
        stmt = select(User).where(User.id == id).options(selectinload(User.role))
        return await self.session.scalar(stmt)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).options(selectinload(User.role))
        return await self.session.scalar(stmt)

    async def get_all(
        self, limit: int = 10, offset: int = 0, email_like: str | None = None
    ) -> list[User]:
        stmt = select(User).options(selectinload(User.role)).order_by(User.created_at)
        if email_like:
            stmt = stmt.where(User.email.ilike(f"%{email_like}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self, email_like: str | None = None) -> int:
        stmt = select(func.count()).select_from(User)
        if email_like:
            stmt = stmt.where(User.email.ilike(f"%{email_like}%"))
        return await self.session.scalar(stmt) or 0

    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user, ["role", "created_at", "updated_at"])
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()
