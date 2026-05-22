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
    store_session,
    rotate_session,
    revoke_device,
    revoke_user,
    list_sessions,
    consume_refresh,
    revoke_refresh,
    revoke_family,
)


class AuthService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def login(self, email: str, password: str, ip: str, ua: str) -> TokenPair:
        user = await self.repo.get_by_email(email)

        if not user or not user.password:
            raise UnauthorizedError("invalid credentials")
        if not verify_password(user.password, plain=password):
            raise UnauthorizedError("invalid credentials")

        access_token = create_access_token(user)
        refresh_token, jti, device = create_refresh_token(user.id)
        # await store_refresh(self.redis, jti, fam, user.id)
        await store_session(self.redis, user.id, device, jti, ip, ua)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, token: str, ip: str) -> TokenPair:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError("invalid token") from e

        user_id = payload["sub"]
        device = payload["device"]
        old_jti = payload["jti"]

        # data = await consume_refresh(self.redis, payload["jti"])
        # if data is None:
        #     raise UnauthorizedError("token revoke or reused")
        new_refresh_token, new_jti, _ = create_refresh_token(user_id, device)
        status = await rotate_session(self.redis, user_id, device, old_jti, new_jti, ip)

        if status == "MISSING":
            raise UnauthorizedError("session expired")
        if status == "REUSE":
            await revoke_user(self.redis, user_id)
            raise UnauthorizedError("token reused")

        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("user not found")

        new_access_token = create_access_token(user)
        return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)

    async def logout(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return

        await revoke_device(self.redis, payload["jti"])

    async def logout_all(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return
        await revoke_user(self.redis, payload["fam"])

    async def sessions(self, user_id: str) -> list[dict]:
        return await list_sessions(self.redis, user_id)
