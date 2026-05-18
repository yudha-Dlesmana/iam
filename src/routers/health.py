from fastapi import APIRouter

from src.lib.deps import HealthServiceDep

router = APIRouter(tags=["Health"])

@router.get("/health")
async def status(service: HealthServiceDep):
    return await service.check_all()
