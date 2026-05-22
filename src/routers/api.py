from fastapi import APIRouter
from src.routers.health import router as health_router
from src.routers.auth import router as auth_router
from src.routers.role import router as role_router
from src.routers.user import router as user_router

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(role_router)
router.include_router(user_router)
