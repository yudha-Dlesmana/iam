import jwt
from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.redis import get_redis
from src.core.security import decode_access_token
from src.repositories.health import HealthRepository
from src.repositories.role import RoleRepository
from src.repositories.user import UserRepository
from src.repositories.permission import PermissionRepository
from src.repositories.service import ServiceRepository
from src.services.health import HealthService
from src.services.auth import AuthService
from src.services.role import RoleService
from src.services.user import UserService
from src.services.permission import PermissionService
from src.services.service import ServiceService
from src.exceptions.base import UnauthorizedError
from src.exceptions.base import ForbiddenError

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]


def get_health_service(session: DbSession, redis: RedisClient) -> HealthService:
    return HealthService(HealthRepository(session, redis))


def get_auth_service(session: DbSession, redis: RedisClient) -> AuthService:
    return AuthService(UserRepository(session), redis)


def get_role_service(session: DbSession) -> RoleService:
    return RoleService(RoleRepository(session), PermissionRepository(session))


def get_user_service(session: DbSession) -> UserService:
    return UserService(UserRepository(session))


def get_permission_service(session: DbSession) -> PermissionService:
    return PermissionService(PermissionRepository(session))


def get_service_service(session: DbSession) -> ServiceService:
    return ServiceService(ServiceRepository(session))


_bearer = HTTPBearer(auto_error=False)


async def get_current_claims(
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if credential is None:
        raise UnauthorizedError("missing bearer token")
    try:
        return decode_access_token(credential.credentials)
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError("invalid access token") from e


CurrentClaims = Annotated[dict, Depends(get_current_claims)]


async def get_current_user_id(claims: CurrentClaims) -> str:
    return claims["sub"]


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


def require_role(*roles: str):
    async def checker(claims: CurrentClaims) -> dict:
        if claims.get("role") not in roles:
            raise ForbiddenError("insufficient role")
        return claims

    return Depends(checker)


def require_permission(*perms: str):
    async def checker(claims: CurrentClaims) -> dict:
        granted = set(claims.get("permissions", []))
        if not granted.issuperset(perms):
            raise ForbiddenError("insufficient permission")
        return claims

    return Depends(checker)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
ServiceServiceDep = Annotated[ServiceService, Depends(get_service_service)]
