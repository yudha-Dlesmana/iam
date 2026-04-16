import asyncio
from sqlalchemy.exc import OperationalError, DatabaseError

from src.repositories.health_repository import HealthRepository

class HealthService:
    def __init__(self, repo: HealthRepository):
        self.repo = repo

    async def check_database(self) -> str:
        try:
            await self.repo.check_db()
            return "connected"
        except OperationalError as e:
            return f"unavailable: connection error: {str(e.orig)}"
        except DatabaseError as e:
            return f"unavailable: database error: {str(e.orig)}"

    async def check_other_service(self) -> str:
        try:
            await asyncio.sleep(0.1)
            return "ok"
        except Exception as e:
            return f"unavailable: {str(e)}"