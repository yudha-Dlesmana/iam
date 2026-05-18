from typing import Annotated
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.redis import get_redis
from src.repositories.role import RoleRepository
from src.repositories.health import HealthRepository
from src.services.role import RoleService
from src.services.health import HealthService

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]

def get_role_service(session: DbSession) -> RoleService:
    return RoleService(RoleRepository(session))

def get_health_service(session: DbSession, redis: RedisClient) -> HealthService:
    return HealthService(HealthRepository(session, redis))

RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]