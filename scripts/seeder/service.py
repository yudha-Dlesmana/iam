from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Service

SERVICE = ["iam"]


async def seed_service(session: AsyncSession) -> None:
    for name in SERVICE:
        exists = await session.scalar(select(Service).where(Service.name == name))
        if exists:
            print(f"= service {name} (skip)")
            continue
        session.add(Service(name=name))
        print(f"+ service {name}")

    await session.commit()
