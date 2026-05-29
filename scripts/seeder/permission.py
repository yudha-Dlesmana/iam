from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Permission

PERMISSIONS = [
    "user.read",
    "user.create",
    "user.update",
    "user.delete",
    "role.read",
    "role.manage",
    "permission.read",
]


async def seed_permission(session: AsyncSession) -> None:
    for name in PERMISSIONS:
        exists = await session.scalar(select(Permission).where(Permission.name == name))
        if exists:
            print(f"= permission {name} (skip)")
            continue
        session.add(Permission(name=name))
        print(f"+ permission {name}")

    await session.commit()
