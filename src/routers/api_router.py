from fastapi import APIRouter

from src.routers.health_router import router as health_router
from src.routers.role_router import router as role_router
from src.routers.user_router import router as user_router
from src.routers.auth_router import router as auth_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(role_router)
api_router.include_router(user_router)
api_router.include_router(auth_router)