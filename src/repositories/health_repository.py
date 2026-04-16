from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class HealthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_db(self) -> None:
        await self.db.execute(text("SELECT 1"))
