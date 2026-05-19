from typing import Annotated
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.redis import get_redis
from src.repositories.health import HealthRepository
from src.repositories.role import RoleRepository
from src.repositories.user import UserRepository
from src.services.health import HealthService
from src.services.role import RoleService
from src.services.user import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]

def get_health_service(session: DbSession, redis: RedisClient) -> HealthService:
    return HealthService(HealthRepository(session, redis))

def get_role_service(session: DbSession) -> RoleService:
    return RoleService(RoleRepository(session))

def get_user_service(session: DbSession) -> UserService:
    return UserService(UserRepository(session))

HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]