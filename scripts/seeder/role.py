from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Role

_ROLES: list[dict] = [
    {"name": "super_admin", "single_session": True},
    {"name": "user", "single_session": False},
]


async def seed_role(session: AsyncSession) -> None:
    for spec in _ROLES:
        exists = await session.scalar(select(Role).where(Role.name == spec["name"]))
        if exists:
            print(f"= role {spec['name']} (skip)")
            continue
        session.add(Role(**spec))
        print(f"+ role {spec['name']}")
    await session.commit()
