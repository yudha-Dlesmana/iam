from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from argon2 import PasswordHasher

from src.models import User, Role

ADMIN="super_admin@starter.com"
PASSWORD="!Qwer123"
ph = PasswordHasher()

async def seed_user(session: AsyncSession) -> None:
    admin_role = await session.scalar(select(Role).where(Role.name == "super_admin"))
    if not admin_role:
        raise RuntimeError("super admin role missing, run seed_roles first")
    
    exists = await session.scalar(select(User).where(User.email == ADMIN))
    if exists:
        print(f"= user {ADMIN} (skip)")
        return

    session.add(User(
        email=ADMIN,
        password=ph.hash(PASSWORD),
        role_id = admin_role.id
    ))

    await session.commit()
    print(f"+ user {ADMIN}")