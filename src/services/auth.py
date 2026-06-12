import jwt
from redis.asyncio import Redis

from src.schemas.auth import TokenPair
from src.repositories.user import UserRepository
from src.exceptions.base import UnauthorizedError, TooManyRequestsError
from src.lib.rate_limit import hit as rl_hit, reset as rl_reset
from src.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    store_session,
    rotate_session,
    revoke_device,
    revoke_user,
    list_sessions,
    get_session,
)
from src.lib.revocation import mark_sid_revoked, mark_revoked
from src.core.logging import get_logger

log = get_logger(__name__)

LOGIN_EMAIL_LIMIT = 5
LOGIN_IP_LIMIT = 20
LOGIN_WINDOW_SECONDS = 15 * 60
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


class AuthService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def _enforce_login_limit(self, email: str, ip: str) -> None:
        email_key = f"login:email:{email.lower()}"
        ip_key = f"login:ip:{ip}" if ip else None

        ok_email, retry_email = await rl_hit(
            self.redis, email_key, LOGIN_EMAIL_LIMIT, LOGIN_WINDOW_SECONDS
        )
        if not ok_email:
            log.warning("login rate limited email=%s", email)
            raise TooManyRequestsError(
                "too many login attempts", retry_after=retry_email
            )

        if ip_key:
            ok_ip, retry_ip = await rl_hit(
                self.redis, ip_key, LOGIN_IP_LIMIT, LOGIN_WINDOW_SECONDS
            )
            if not ok_ip:
                log.warning("login rate limited ip=%s", ip)
                raise TooManyRequestsError(
                    "too many login attempts", retry_after=retry_ip
                )

    async def login(self, email: str, password: str, ip: str, ua: str) -> TokenPair:
        await self._enforce_login_limit(email, ip)

        user = await self.repo.get_by_email(email)

        if not user or not user.password:
            verify_password(_DUMMY_HASH, plain=password)
            log.warning("login failed: unknown email=%s", email)
            raise UnauthorizedError("invalid credentials")
        if not verify_password(user.password, plain=password):
            log.warning("login failed: wrong password user=%s", user.id)
            raise UnauthorizedError("invalid credentials")

        await rl_reset(self.redis, f"login:email:{email.lower()}")

        if user.role and user.role.single_session:
            await revoke_user(self.redis, user.id)
            log.info("single-session enforced: revoked prior sessions user=%s", user.id)

        refresh_token, jti, device = create_refresh_token(user.id)
        access_token = create_access_token(user, sid=device)
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

        new_access_token = create_access_token(user, sid=device)
        return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)

    async def logout(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return

        await revoke_device(self.redis, payload["sub"], payload["device"])
        await mark_sid_revoked(self.redis, payload["device"])

    async def logout_all(self, token: str) -> None:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError:
            return
        await revoke_user(self.redis, payload["sub"])
        await mark_revoked(self.redis, payload["sub"])

    async def sessions(self, user_id: str) -> list[dict]:
        return await list_sessions(self.redis, user_id)

    async def current_session(self, token: str, user_id: str) -> dict:
        try:
            payload = decode_refresh_token(token)
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError("invalid token") from e

        if payload["sub"] != user_id:
            raise UnauthorizedError("token mismatch")

        session = await get_session(self.redis, user_id, payload["device"])
        if session is None:
            raise UnauthorizedError("session expired")
        return session
