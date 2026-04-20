import asyncio
from sqlalchemy.exc import OperationalError, DatabaseError

from src.repositories.health_repository import HealthRepository

DB_TIMEOUT = 5.0
SERVICE_TIMEOUT = 3.0

class HealthService:
    def __init__(self, repo: HealthRepository):
        self.repo = repo

    async def check_database(self) -> str:
        try:
            await asyncio.wait_for(self.repo.check_db(), timeout=DB_TIMEOUT)
            return "connected"
        except asyncio.TimeoutError:
            return f"unavailable: timed out after {DB_TIMEOUT}s"
        except OperationalError as e:
            return f"unavailable: connection error: {str(e.orig)}"
        except DatabaseError as e:
            return f"unavailable: database error: {str(e.orig)}"
        except Exception as e:
            return f"unavailable: {str(e)}"

    async def check_other_service(self) -> str:
        try:
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=SERVICE_TIMEOUT)
            return "ok"
        except asyncio.TimeoutError:
            return f"unavailable: timed out after {SERVICE_TIMEOUT}s"
        except Exception as e:
            return f"unavailable: {str(e)}"