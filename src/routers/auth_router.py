from src.core.csrf import verify_csrf
from src.core.dependency import get_refresh_token
from src.core.dependency import get_access_token
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import APIRouter, Depends, Response, Cookie

from src.core.config import settings
from src.core.dependency import get_auth_service, get_current_user, bearer_scheme
from src.core.cookies import set_auth_cookie, clear_auth_cookie
from src.services.auth_service import AuthService
from src.models import User
from src.schemas.user_schema import UserResponse
from src.schemas.auth_schema import TokenBundle, LoginRequest, LoginResponse
from src.schemas.base_schema import BaseResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/login",
    response_model=BaseResponse[UserResponse]
)
async def login(
    request: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service)
):
    result: LoginResponse = await service.login(request)
    set_auth_cookie(
        response,
        access_token=result.tokens.access_token, 
        refresh_token=result.tokens.refresh_token, 
        csrf_token=result.tokens.csrf_token
    )
    return BaseResponse(
        message="Login successful",
        data=result.user
    )

@router.post(
    "/refresh",
    response_model=BaseResponse[None]
)
async def refresh(
    response: Response,
    refresh_token: str = Depends(get_refresh_token),
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
    response_model=BaseResponse[None],
    dependencies=[Depends(verify_csrf)]
)
async def logout(
    response: Response,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
    refresh_token: str = Depends(get_refresh_token)
):
    await service.logout(
        access_token=access_token,
        refresh_token=refresh_token,
        current_user_id=current_user.id
    )
    clear_auth_cookie(
        response)
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