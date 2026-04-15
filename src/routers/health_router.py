import asyncio
from fastapi import APIRouter, Depends
from src.services.health_services import HealthService
from src.core.dependency import get_health_service



router = APIRouter()

@router.get("/health")
async def health(service: HealthService = Depends(get_health_service)):
    db_status, other_status = await asyncio.gather(
        service.check_database(),
        service.check_other_service(),
    )
    return {
        "status": "running",
        "database": db_status,
        "other_service": other_status
    }