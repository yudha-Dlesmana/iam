from src.repositories.health import HealthRepository


class HealthService:
    def __init__(self, repo: HealthRepository):
        self.repo = repo

    async def _check(self, coro) -> dict:
        try:
            await coro
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def check_all(self) -> dict:
        db = await self._check(self.repo.ping_db())
        redis = await self._check(self.repo.ping_redis())
        all_ok = db["status"] == "ok" and redis["status"] == "ok"
        return {
            "status": "ok" if all_ok else "degraded",
            "app": "running",
            "database": db,
            "redis": redis,
        }

