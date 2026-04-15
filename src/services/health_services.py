import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class HealthService:
    def __init__(self, db:AsyncSession):
        self.db = db

    async def check_database(self) -> str:
        try:
            await self.db.execute(text("SELECT 1"))
            return "connected"
        except Exception as e:
            return f"unavailable: {str(e)}"

    async def check_other_service(self) -> str:
        try:
            await asyncio.sleep(0.1)
            return "ok"
        except Exception as e:
            return f"unavailable: {str(e)}"