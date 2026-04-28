from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

from src.schemas.auth_schema import RefreshTokenData, AccessTokenData, TokenPair
from src.schemas.oauth_schema import GoogleUserInfo, OAuhtCreateRequest
from src.repositories.user_repository import UserRepository
from src.repositories.oauth_repository import OAuthRepository
from src.core.security import create_token
from src.core.config import settings
from src.core.google_oauth import google_oauth


class OAuthService:
    def __init__(
        self,
        oauth_repo: OAuthRepository,
        user_repo: UserRepository
    ):
        self.oauth_repo = oauth_repo
        self.user_repo = user_repo
    
    def get_google_auth_url(
        self
    ) -> str:
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "email profile openid",
            "access_type": "offline"
        }

        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def google_callback(
        self,
        code: str
    )-> TokenPair:
        google_user: GoogleUserInfo = await google_oauth(code)

        user = await self.oauth_repo.get_user_by_oauth("google", google_user.sub)
        if not user:
            user = await self.user_repo.get_user_by_email(google_user.email)
            if user:
                await self.oauth_repo.create_oauth_account_for_existing_user(
                    user_id=user.id, 
                    provider="google", 
                    provider_user_id=google_user.sub
                )
            else:
                user = await self.oauth_repo.create_oauth_user(
                    request=OAuhtCreateRequest(
                        email=google_user.email,
                        provider="google",
                        provider_user_id=google_user.sub
                    )
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