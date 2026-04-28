from src.schemas.auth_schema import TokenResponse
from src.schemas.base_schema import BaseResponse
from src.core.dependency import get_oauth_service
from src.services.oauth_service import OAuthService
from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse

from src.core.config import settings

router = APIRouter(prefix="/oauth", tags=["OAuth"])

@router.get("/google/login")
async def google_login(
    service: OAuthService = Depends(get_oauth_service)
):
    url = service.get_google_auth_url()
    return RedirectResponse(url)

@router.get("/google/callback", response_model=BaseResponse[TokenResponse])
async def google_callback(
    code: str,
    response: Response,
    service: OAuthService = Depends(get_oauth_service)
):
    pair = await service.google_callback(code)
    response.set_cookie(
        key="refresh_token",
        value=pair.refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict" if settings.is_production else "lax"
    )
    return BaseResponse(
        message="Login successful",
        data=TokenResponse(access_token=pair.access_token)
    )