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
    peek_session,
    store_session,
    rotate_session,
    revoke_device,
    revoke_user,
    list_sessions,
)
from src.core.logging import get_logger

log = get_logger(__name__)


class AuthService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def login(self, email: str, password: str, ip: str, ua: str) -> TokenPair:
        user = await self.repo.get_by_email(email)

        if not user or not user.password:
            log.warning("login failed: unknown email=%s", email)
            raise UnauthorizedError("invalid credentials")
        if not verify_password(user.password, plain=password):
            log.warning("login failed: wrong password user=%s", user.id)
            raise UnauthorizedError("invalid credentials")

        access_token = create_access_token(user)
        refresh_token, jti, device = create_refresh_token(user.id)
        await store_session(self.redis, user.id, device, jti, ip, ua)
        log.info("login success user=%s", user.id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, token: str, ip: str) -> TokenPair:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError("invalid token") from e

        user_id = payload["sub"]
        device = payload["device"]
        old_jti = payload["jti"]

        new_refresh_token, new_jti, _ = create_refresh_token(user_id, device)
        status = await rotate_session(self.redis, user_id, device, old_jti, new_jti, ip)

        if status == "MISSING":
            raise UnauthorizedError("session expired")
        if status == "REUSE":
            await revoke_user(self.redis, user_id)
            log.warning("refresh REUSE detected user=%s, all sessions revoked", user_id)
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

        await revoke_device(self.redis, payload["sub"], payload["device"])

    async def logout_all(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return
        await revoke_user(self.redis, payload["sub"])

    async def validate(self, token: str) -> bool:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return False
        return await peek_session(
            self.redis, payload["sub"], payload["device"], payload["jti"]
        )

    async def sessions(self, user_id: str) -> list[dict]:
        return await list_sessions(self.redis, user_id)
