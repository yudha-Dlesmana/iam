from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

class HealthRepository:
    def __init__(
        self, 
        db: AsyncSession,
        redis: Redis
    ):
        self.db = db
        self.redis = redis
    
    
    async def check_db(
        self
    ) -> None:
        await self.db.execute(text("SELECT 1"))

    async def check_redis(
        self
    ) -> None:
        await self.redis.ping()