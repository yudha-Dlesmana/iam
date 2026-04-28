from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.oauth_account import OAuthAccount
from src.models.user import User
from src.schemas.oauth_schema import OAuhtCreateRequest

class OAuthRepository:
    def __init__(
        self, 
        db: AsyncSession
    ):
        self.db = db

    async def get_user_by_oauth(
        self,
        provider: str,
        provider_user_id: str,
    ) -> User | None:
        result = await self.db.execute(
            select(User)
            .join(OAuthAccount, OAuthAccount.user_id == User.id)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_oauth_user(
        self,
        request: OAuhtCreateRequest
    ) -> User:
        user = User(
            email=request.email,
            password=None,
            role_id=request.role_id
        )
        self.db.add(user)
        await self.db.flush()

        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=request.provider,
            provider_user_id=request.provider_user_id
        )
        self.db.add(oauth_account)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def create_oauth_account_for_existing_user(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str
    ) -> OAuthAccount:
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            providers_user_id=provider_user_id
        )
        self.db.add(oauth_account)
        await self.db.commit()
        await self.db.refresh(oauth_account)
        return oauth_account