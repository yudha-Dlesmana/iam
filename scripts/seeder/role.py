from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Role

async def seed_role(session: AsyncSession) -> None:
    roles =["super_admin", "user"]
    for name in roles:
        exists = await session.scalar(select(Role).where(Role.name == name))
        if exists:
            print(f"= user {name} (skip)")
            continue
        session.add(Role(name=name))
        print(f"+ role {name}")
    await session.commit()
