from fastapi.security import HTTPAuthorizationCredentials
from fastapi import APIRouter, Depends, Response, Cookie

from src.core.config import settings
from src.core.dependency import get_auth_service, get_current_user, bearer_scheme
from src.core.cookies import set_auth_cookie, clear_auth_cookie
from src.services.auth_service import AuthService
from src.models import User
from src.schemas.user_schema import UserResponse
from src.schemas.auth_schema import TokenBundle, TokenResponse, LoginRequest
from src.schemas.base_schema import BaseResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/login",
    response_model=BaseResponse[TokenResponse]
)
async def login(
    request: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service)
):
    bundle: TokenBundle = await service.login(request)
    set_auth_cookie(
        response,
        access_token=bundle.access_token, 
        refresh_token=bundle.refresh_token, 
        csrf_token=bundle.csrf_token)
    return BaseResponse(
        message="Login successful",
    )

@router.post(
    "/refresh",
    response_model=BaseResponse[TokenResponse]
)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(..., include_in_schema=False),
    service: AuthService = Depends(get_auth_service)
):
    bundle = await service.refresh(refresh_token)
    set_auth_cookie(
        response, 
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        csrf_token=bundle.csrf_token)
    return BaseResponse(
        message="Token refreshed",
    )

@router.post(
    "/logout", 
    response_model=BaseResponse[None]
)
async def logout(
    response: Response,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    refresh_token: str = Cookie(..., include_in_schema=False)
):
    await service.logout(
        access_token=credentials.credentials,
        refresh_token=refresh_token,
        current_user_id=current_user.id
    )
    response.delete_cookie("refresh_token")
    return BaseResponse(
        message="Logged out"
    )

@router.get(
    "/me", 
    response_model=BaseResponse[UserResponse]
)
async def me(
    current_user: User = Depends(get_current_user)
):
    return BaseResponse(
        message="User fetched",
        data=UserResponse.model_validate(current_user)
    )