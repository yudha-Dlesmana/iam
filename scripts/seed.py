import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import SessionLocal, engine
from src.core.security import hash_password
from src.models import Role, User

# ---- constant seed ----
ROLES = ["admin", "user"]
ADMIN_EMAIL = "admin@starter.com"
ADMIN_PASSWORD = "!Qwer123"

# ---- fungsi seed ----
async def seed_roles(db: AsyncSession) -> None:
    existing = (await db.scalars(select(Role.name))).all()
    missing = [name for name in ROLES if name not in existing]

    for name in missing:
        db.add(Role(name=name))

    if missing:
        await db.flush()
        print(f"roles created: {missing}")
    else:
        print("roles already seeded")


async def seed_admin(db: AsyncSession) -> None:
    existing = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    if existing:
        print(f"admin already exists: {ADMIN_EMAIL}")
        return
    
    admin_role = await db.scalar(select(Role).where(Role.name == 'admin'))
    if not admin_role:
        raise RuntimeError("admin role missing - run seed_roles first")

    db.add(User(
        email=ADMIN_EMAIL,
        password=hash_password(ADMIN_PASSWORD),
        role_id=admin_role.id
    ))
    print(f"admin created: {ADMIN_EMAIL}")

# ---- entrypoint ----
async def main():
    async with SessionLocal() as db:
        await seed_roles(db)
        await seed_admin(db)
        await db.commit()
    await engine.dispose()
    print("seed done")


if __name__ == "__main__":
    asyncio.run(main())