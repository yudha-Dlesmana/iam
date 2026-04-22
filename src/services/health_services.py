import asyncio
from sqlalchemy.exc import OperationalError, DatabaseError

from src.core.config import settings
from src.schemas.base_schema import BaseResponse
from src.schemas.health_schema import HealthResponse
from src.repositories.health_repository import HealthRepository


DB_TIMEOUT = 5.0
SERVICE_TIMEOUT = 3.0

def _db_label() -> str:
    url = settings.DB_URL.lower()
    if "mysql" in url:
        return "mysql"
    if "postgresql" in url or "postgres" in url:
        return "postgresql"
    return "database"

class HealthService:
    def __init__(
        self,
        repo: HealthRepository
    ):
        self.repo = repo

    async def check_database(
        self
    ) -> str:
        label = _db_label()
        try:
            await asyncio.wait_for(self.repo.check_db(), timeout=DB_TIMEOUT)
            return f"connected to {label}"
        except asyncio.TimeoutError:
            return f"{label} unavailable: timed out after {DB_TIMEOUT}s"
        except OperationalError as e:
            return f"{label} unavailable: connection error: {str(e.orig)}"
        except DatabaseError as e:
            return f"{label} unavailable: database error: {str(e.orig)}"


    async def check_redis(
        self
    ) -> str:
        try:
            await asyncio.wait_for(self.repo.check_redis(), timeout=DB_TIMEOUT)
            return "connected"
        except asyncio.TimeoutError:
            return f"unavailable: timed out after {DB_TIMEOUT}s"
        except Exception as e:
            return f"unavailale:{str(e)}"


    async def check_other_service(
        self
    ) -> str:
        try:
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=SERVICE_TIMEOUT)
            return "ok"
        except asyncio.TimeoutError:
            return f"unavailable: timed out after {SERVICE_TIMEOUT}s"
        except Exception as e:
            return f"unavailable: {str(e)}"

    async def get_health(
        self
    ) -> BaseResponse[HealthResponse]:
        db_status, redis_status,other_status = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_other_service(),
        )
        return BaseResponse(
            message="Health checked",
            data=HealthResponse(
                status="running",
                database=db_status,
                redis=redis_status,
                other_service=other_status
            )
        )
    