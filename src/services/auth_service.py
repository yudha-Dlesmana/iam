from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

from src.core.security import verify_password, decode_token, create_token
from src.core.config import settings
from src.schemas.auth_schema import LoginRequest, TokenPair, AccessTokenData, RefreshTokenData
from src.repositories.user_repository import UserRepository


class AuthService:
    def __init__(
        self,
        repo: UserRepository
    ):
        self.repo = repo

    async def login(
        self,
        request = LoginRequest
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
        # --- blacklist refresh token on redish ---
        #
        # -----------------------------------------
        
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
