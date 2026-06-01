import time

from redis.asyncio import Redis

from src.core.security import ACCESS_TTL


_REVOCATION_TTL = int(ACCESS_TTL.total_seconds()) + 5


def _key(user_id: str) -> str:
    return f"revoked:user:{user_id}"


async def mark_revoked(r: Redis, user_id: str) -> int:
    """Mark all access tokens for user issued at or before now as revoked.

    Returns the timestamp written.
    """
    now = int(time.time())
    await r.set(_key(user_id), now, ex=_REVOCATION_TTL)
    return now


async def get_revoked_at(r: Redis, user_id: str) -> int | None:
    val = await r.get(_key(user_id))
    return int(val) if val else None


async def is_token_revoked(r: Redis, user_id: str, iat: int) -> bool:
    revoked_at = await get_revoked_at(r, user_id)
    return revoked_at is not None and iat <= revoked_at
