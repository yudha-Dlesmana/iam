import secrets
import secrets
from uuid import uuid4
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis

from src.core.security import verify_password, create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from src.core.config import settings
from src.schemas.auth_schema import LoginRequest, TokenBundle, AccessTokenData, RefreshTokenData
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
    ) -> TokenBundle:
        # CHECK CREDENTIALS
        user = await self.repo.get_user_by_email(request.email)
        if not user or not user.password or not verify_password(request.password, user.password):
            raise HTTPException(
                status_code=401, 
                detail="invalid email or password"
            )
        
        # CREATE TOKEN PAYLOAD
        access_payload = AccessTokenData(
            sub=user.id,
            role=user.role.name if user.role else None,
            exp=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_payload = RefreshTokenData(
            sub=user.id,
            jti= str(uuid4()),
            exp=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        # CREATE WHITELIST REFRESH TOKEN
        ttl = int(
            refresh_payload.exp.timestamp() - datetime.now(timezone.utc).timestamp()
        )
        await self.redis.set(
            f"refresh:{refresh_payload.jti}", user.id, ex=ttl
        )
        
        return TokenBundle(
            access_token=create_access_token(access_payload),
            refresh_token=create_refresh_token(refresh_payload),
            csrf_token=secrets.token_urlsafe(32)
        )
    
    async def refresh(
        self,
        refresh_token: str 
    ) -> TokenBundle:
        # DECODE REFRESH TOKEN 
        refresh_payload: RefreshTokenData = decode_refresh_token(refresh_token)

        # CHECK WHITELIST
        store_user_id = await self.redis.get(f"refresh:{refresh_payload.jti}")
        if store_user_id is None:
            raise HTTPException(
                status_code=401 , 
                detail="Token revoked or invalid"
            )

        # CHECK USER
        user = await self.repo.get_user_by_id(refresh_payload.sub)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        # ROTATION WHITELIST: DELETE 
        await self.redis.delete(f"refresh:{refresh_payload.jti}")

        # NEW TOKEN
        access_payload = AccessTokenData(
            sub=user.id,
            role=user.role.name if user.role else None,
            exp=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_payload = RefreshTokenData(
            sub=user.id,
            jti=str(uuid4),
            exp=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        # ROTATION WHITELIST: CREATE 
        ttl = int(refresh_payload.exp.timestamp() - datetime.now(timezone.utc).timestamp())
        await self.redis.set(f"refresh:{refresh_token}", user.id, ex=ttl)

        # RETURN ACCESS AND REFRESH TOKEN 
        return TokenBundle(
            access_token=create_access_token(access_payload),
            refresh_token=create_refresh_token(refresh_payload),
            csrf_token=secrets.token_urlsafe(32)
        )

    async def logout(
        self,
        access_token: str,
        refresh_token: str,
        current_user_id: str,
    ) -> None:
        access_payload: AccessTokenData = decode_access_token(access_token)
        refresh_payload: RefreshTokenData = decode_refresh_token(refresh_token) 

        if not (current_user_id == access_payload.sub == refresh_payload.sub):
            raise HTTPException(
                status_code=401,
                detail="Invalid Credentials"
            )

        ttl = int(refresh_payload.exp.timestamp() - datetime.now(timezone.utc).timestamp())

        await self.redis.set(f"blacklist:{refresh_payload.jti}", "1", ex=ttl)