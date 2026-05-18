from typing import Awaitable, cast

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis

    async def ping_db(self) -> None:
        await self.session.execute(text("SELECT 1"))

    async def ping_redis(self) -> None:
        await cast(Awaitable[bool], self.redis.ping())
