from fastapi import status, Cookie
from src.services.oauth_service import OAuthService
from src.core.redis_client import get_redis
from redis.asyncio import Redis
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.models import User
from src.core.database import get_db
from src.core.security import decode_access_token
from src.services.health_services import HealthService
from src.services.role_services import RoleService
from src.services.user_service import UserService
from src.services.auth_service import AuthService
from src.repositories.health_repository import HealthRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository
from src.repositories.oauth_repository import OAuthRepository

bearer_scheme= HTTPBearer()

def get_health_service(
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis)
) -> HealthService:
    repo = HealthRepository(db, redis)

    return HealthService(repo)

def get_role_service(
    db: AsyncSession = Depends(get_db)
) -> RoleService:
    repo = RoleRepository(db)
    return RoleService(repo)

def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    repo = UserRepository(db)
    return UserService(repo)

def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo, redis)

def get_oauth_service(
    db: AsyncSession = Depends(get_db)
) -> OAuthService:
    oauth_repo = OAuthRepository(db)
    user_repo = UserRepository(db)
    return OAuthService(oauth_repo, user_repo)

async def get_access_token(
    access_token: str = Cookie(..., alias="access_token", include_in_schema=False),
) -> str:
    return access_token

async def get_refresh_token(
    refresh_token: str = Cookie(..., alias="refresh_token", include_in_schema=False)
) -> str:
    return refresh_token

async def get_current_user(
    access_token: str = Depends(get_access_token),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    payload = decode_access_token(access_token)
    if await redis.exists(f"blacklist:{payload.jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked"
        )
    
    user = await UserRepository(db).get_user_by_id(payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user