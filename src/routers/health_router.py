from fastapi import APIRouter, Depends

from src.core.dependency import get_health_service
from src.schemas.base_schema import BaseResponse
from src.schemas.health_schema import HealthResponse
from src.services.health_services import HealthService


router = APIRouter(prefix="/health", tags=["Health"])

@router.get(
    "/health", 
    status_code=200,
    response_model=BaseResponse[HealthResponse]
)
async def health(
    service: HealthService = Depends(get_health_service)
):
    return await service.get_health()