from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.core.database import get_db
from src.services.health_services import HealthService
from src.repositories.health_repository import HealthRepository

def get_health_service(db: AsyncSession = Depends(get_db)) -> HealthService:
    repo = HealthRepository(db)
    return HealthService(repo)