import asyncio

from src.core.database import SessionLocal
from scripts.seeders.role import seed_roles

async def seed() -> None:
    async with SessionLocal() as session:
        await seed_roles(session)
    print("✓ seed complete")


if __name__ == "__main__":
    asyncio.run(seed())