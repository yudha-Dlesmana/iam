import time

from redis.asyncio import Redis

from src.core.security import ACCESS_TTL
from src.exceptions.base import UnauthorizedError


_REVOCATION_TTL = int(ACCESS_TTL.total_seconds()) + 5


def _key(user_id: str) -> str:
    return f"revoked:user:{user_id}"


def _sid_key(sid: str) -> str:
    return f"revoked:sid:{sid}"


async def mark_revoked(r: Redis, user_id: str) -> int:
    now = int(time.time())
    await r.set(_key(user_id), now, ex=_REVOCATION_TTL)
    return now


async def mark_sid_revoked(r: Redis, sid: str) -> None:
    await r.set(_sid_key(sid), 1, ex=_REVOCATION_TTL)


async def get_revoked_at(r: Redis, user_id: str) -> int | None:
    val = await r.get(_key(user_id))
    return int(val) if val else None


async def is_token_revoked(r: Redis, user_id: str, iat: int) -> bool:
    revoked_at = await get_revoked_at(r, user_id)
    return revoked_at is not None and iat <= revoked_at


async def is_sid_revoked(r: Redis, sid: str) -> bool:
    return await r.exists(_sid_key(sid))


async def is_revoked(r: Redis, user_id: str, iat: int, sid: str | None) -> None:
    keys = [f"revoked:user:{user_id}"]
    if sid:
        keys.append(f"revoked:sid:{sid}")

    vals = await r.mget(*keys)
    if vals[0] and iat <= int(vals[0]):
        raise UnauthorizedError("token revoked")
    if sid and vals[1]:
        raise UnauthorizedError("session revoked")
