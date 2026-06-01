from src.core.config import settings
from src.core.logging import get_logger
from src.repositories.health import HealthRepository

log = get_logger(__name__)


class HealthService:
    def __init__(self, repo: HealthRepository):
        self.repo = repo

    async def _check(self, coro, name: str) -> dict:
        try:
            await coro
            return {"status": "ok"}
        except Exception as e:
            log.exception("health check failed: %s", name)
            result = {"status": "error"}
            if not settings.is_production:
                result["detail"] = str(e)
            return result

    async def check_all(self) -> dict:
        db = await self._check(self.repo.ping_db(), "database")
        redis = await self._check(self.repo.ping_redis(), "redis")
        all_ok = db["status"] == "ok" and redis["status"] == "ok"
        return {
            "status": "ok" if all_ok else "degraded",
            "app": "running",
            "database": db,
            "redis": redis,
        }

