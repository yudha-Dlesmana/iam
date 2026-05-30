from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Role, Permission

GRANTS: dict[str, list[str]] = {"super_admin": ["*"], "user": ["iam.user.read"]}


async def seed_role_permission(session: AsyncSession) -> None:
    all_perm = list(await session.scalars(select(Permission)))
    by_name = {p.name: p for p in all_perm}

    for role_name, perm_names in GRANTS.items():
        role = await session.scalar(
            select(Role)
            .where(Role.name == role_name)
            .options(selectinload(Role.permissions))
        )
        if not role:
            print(f"! role {role_name} missing (skip)")
            continue

        wanted = (
            all_perm
            if perm_names == ["*"]
            else [by_name[n] for n in perm_names if n in by_name]
        )
        role.permissions = wanted
        print(f"= role {role_name} -> {[p.name for p in wanted]}")

    await session.commit()
