from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.models import User
from src.core.database import get_db
from src.core.security import decode_token
from src.services.health_services import HealthService
from src.services.role_services import RoleService
from src.services.user_service import UserService
from src.services.auth_service import AuthService
from src.repositories.health_repository import HealthRepository
from src.repositories.role_repository import RoleRepository
from src.repositories.user_repository import UserRepository

bearer_scheme= HTTPBearer()

def get_health_service(
    db: AsyncSession = Depends(get_db)
) -> HealthService:
    repo = HealthRepository(db)
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
    db: AsyncSession = Depends(get_db)
) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.type != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type"
        )
    user = await UserRepository(db).get_user_by_id(payload.sub)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    return user