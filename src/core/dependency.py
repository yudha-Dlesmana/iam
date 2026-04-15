from src.core.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession
from src.services.health_services import HealthService

def get_health_service(db: AsyncSession = Depends(get_db)) -> HealthService:
    return HealthService(db)