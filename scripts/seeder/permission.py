from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Permission, Service

PERMISSIONS: dict[str, list[str]] = {
    "iam": [
        "user.read",
        "user.create",
        "user.update",
        "user.delete",
        "role.read",
        "role.manage",
        "service.read",
        "service.manage",
        "permission.read",
        "permission.manage",
    ]
}


async def seed_permission(session: AsyncSession) -> None:
    for service_name, permissions in PERMISSIONS.items():
        service = await session.scalar(
            select(Service).where(Service.name == service_name)
        )
        if not service:
            print(f"! service {service_name} missing skip")
            continue

        for permission in permissions:
            full_name = f"{service_name}.{permission}"

            exists = await session.scalar(
                select(Permission).where(Permission.name == full_name)
            )
            if exists:
                print(f"= permission {full_name} (skip)")
                continue
            session.add(Permission(name=full_name, service_id=service.id))
            print(f"+ permission {full_name}")

    await session.commit()
