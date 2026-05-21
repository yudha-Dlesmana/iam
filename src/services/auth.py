import jwt
from redis.asyncio import Redis

from src.schemas.auth import TokenPair
from src.repositories.user import UserRepository
from src.exceptions.base import UnauthorizedError
from src.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    store_refresh,
    consume_refresh,
    revoke_refresh,
    revoke_family,
)


class AuthService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.repo.get_by_email(email)

        if not user or not user.password:
            raise UnauthorizedError("invalid credentials")
        if not verify_password(user.password, plain=password):
            raise UnauthorizedError("invalid credentials")

        access_token = create_access_token(user)
        refresh_token, jti, fam = create_refresh_token(user.id)
        await store_refresh(self.redis, jti, fam, user.id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, token: str) -> TokenPair:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError("invalid token") from e

        data = await consume_refresh(self.redis, payload["jti"])
        if data is None:
            raise UnauthorizedError("token revoke or reused")

        user = await self.repo.get_by_id(data["sub"])
        if not user:
            raise UnauthorizedError("user not found")

        access_token = create_access_token(user)
        refresh_token, jti, fam = create_refresh_token(user.id, fam=data["fam"])
        await store_refresh(self.redis, jti, fam, user.id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def logout(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return

        await revoke_refresh(self.redis, payload["jti"])

    async def logout_all(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return
        await revoke_family(self.redis, payload["fam"])
