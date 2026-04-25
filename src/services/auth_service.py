from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis

from src.core.security import verify_password, decode_token, create_token
from src.core.config import settings
from src.schemas.auth_schema import LoginRequest, TokenPair, AccessTokenData, RefreshTokenData
from src.repositories.user_repository import UserRepository


class AuthService:
    def __init__(
        self,
        repo: UserRepository,
        redis: Redis
    ):
        self.repo = repo
        self.redis = redis

    async def login(
        self,
        request: LoginRequest
    ) -> TokenPair:
        user = await self.repo.get_user_by_email(request.email)

        if not user or not verify_password(request.password, user.password):
            raise HTTPException(
                status_code=401, 
                detail="invalid email or password"
            )
        
        access_token_payload = AccessTokenData(
            sub=user.id,
            role=user.role_id,
            exp=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token_payload = RefreshTokenData(
            sub=user.id,
            exp=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        )

        return TokenPair(
            access_token=create_token(access_token_payload),
            refresh_token=create_token(refresh_token_payload)
        )
    
    
    async def refresh(
        self,
        refresh_token: str 
    ) -> TokenPair:
        if await self.redis.exists(f"blacklist:{refresh_token}"):
            raise HTTPException(
                status_code=401, 
                detail="Token revoked"
            )

        payload: RefreshTokenData = decode_token(refresh_token)
        if payload.type != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        user = await self.repo.get_user_by_id(payload.sub)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        access_token_payload = AccessTokenData(
            sub=user.id,
            role=user.role_id,
            exp=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token_payload = RefreshTokenData(
            sub=user.id,
            exp=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        )
        
        ttl = int(payload.exp.timestamp() - datetime.now(timezone.utc).timestamp())
        await self.redis.set(f"blacklist:{refresh_token}", "1", ex=ttl)

        return TokenPair(
            access_token=create_token(access_token_payload),
            refresh_token=create_token(refresh_token_payload)
        )

    async def logout(
        self,
        access_token: str,
        refresh_token: str,
        current_user_id: str,
    ) -> None:
        payload_access_token: AccessTokenData = decode_token(access_token)
        payload_refresh_token: RefreshTokenData = decode_token(refresh_token) 

        if not (current_user_id == payload_access_token.sub == payload_refresh_token.sub):
            raise HTTPException(
                status_code=401,
                detail="Invalid Credentials"
            )

        ttl_access_token = int(payload_access_token.exp.timestamp() - datetime.now(timezone.utc).timestamp())
        ttl_refresh_token = int(payload_refresh_token.exp.timestamp() - datetime.now(timezone.utc).timestamp())

        await self.redis.set(f"blacklist:{access_token}", "1", ex=ttl_access_token)
        await self.redis.set(f"blacklist:{refresh_token}", "1", ex=ttl_refresh_token)