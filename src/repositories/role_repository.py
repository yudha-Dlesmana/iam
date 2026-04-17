from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.role import Role
from src.schemas.role_schema import RoleRequest

class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> list[Role]:
        result = await self.db.execute(select(Role))

        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: int ) -> Role | None:
        result = await self.db.get(Role, role_id)

        return result


    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.name == name))

        return result.scalars().first()

    async def create_role(self, request: RoleRequest) -> Role:
        new_role = Role(name=request.name)

        self.db.add(new_role)
        await self.db.commit()
        await self.db.refresh(new_role)

        return new_role
    
    async def update_role(self, role_id: int, request: RoleRequest) -> Role | None:
        role = await self.db.get(Role, role_id)

        if not role:
            return None

        role.name = request.name
        await self.db.commit()
        await self.db.refresh(role)

        return role

    async def delete_role(self, role_id: int) -> bool:
        role = await self.db.get(Role, role_id)
        
        if not role:
            return False

        await self.db.delete(role)
        await self.db.commit()

        return True
