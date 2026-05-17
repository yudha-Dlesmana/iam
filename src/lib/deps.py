from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.role import RoleRepository
from src.services.role import RoleService

DbSession = Annotated[AsyncSession, Depends(get_db)]

def get_role_service(session: DbSession) -> RoleService:
    return RoleService(RoleRepository(session))

RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]