import asyncio

from src.core.database import SessionLocal, engine
from scripts.seeder.role import seed_role
from scripts.seeder.user import seed_user
from scripts.seeder.permission import seed_permission


async def seed() -> None:
    async with SessionLocal() as session:
        await seed_role(session)
        await seed_user(session)
        await seed_permission(session)
    await engine.dispose()
    print("✓ seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
