from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.core.database import get_db
from src.services.health_services import HealthService
from src.services.role_services import RoleService
from src.services.user_service import UserService
from src.repositories.health_repository import HealthRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository

def get_health_service(db: AsyncSession = Depends(get_db)) -> HealthService:
    repo = HealthRepository(db)
    return HealthService(repo)

def get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    repo = RoleRepository(db)
    return RoleService(repo)

def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    repo = UserRepository(db)
    return UserService(repo)