import asyncio

from src.core.database import SessionLocal
from scripts.seeder.role import seed_role
from scripts.seeder.user import seed_user

async def seed() -> None:
    async with SessionLocal() as session:
        await seed_role(session)
        await seed_user(session)
    print("✓ seed complete")

if __name__ == "__main__"