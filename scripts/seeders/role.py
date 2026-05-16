from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Role

async def seed_roles(session: AsyncSession) -> None:
    roles = ["super admin", "user"]
    for name in roles:
        exists = await session.scalar(select(Role).where(Role.name == name))
        if not exists:
            session.add(Role(name))
            print(f"+ role {name}")
    await session.commit()