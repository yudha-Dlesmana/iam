from typing import Annotated
from fastapi import APIRouter, Cookie, Response, status

from src.core.config import settings
from src.core.security import REFRESH_TTL
from src.exceptions.base import UnauthorizedError
from src.lib.deps import AuthServiceDep, CurrentUserId, UserServiceDep
from src.schemas.auth import LoginRequest, TokenResponse
from src.schemas.user import UserResponse


router = APIRouter(prefix="/auth", tags=["authentication"])

REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/v1/auth"
_SAMESITE = "none" if settings.is_production else "lax"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite=_SAMESITE,
        max_age=int(REFRESH_TTL.total_seconds()),
        path=COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, service: AuthServiceDep):
    pair = await service.login(data.email, data.password)
    _set_refresh_cookie(response, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    if not refresh_token:
        raise UnauthorizedError("missing refresh token")
    pair = await service.refresh(refresh_token)
    _set_refresh_cookie(response, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    if refresh_token:
        await service.logout(refresh_token)
    response.delete_cookie(
        REFRESH_COOKIE,
        httponly=True,
        secure=True,
        samesite="none",
        path=COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


@router.post("/all-logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    if refresh_token:
        await service.logout(refresh_token)
    response.delete_cookie(
        REFRESH_COOKIE,
        httponly=True,
        secure=True,
        samesite="none",
        path=COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


@router.get("/current-user", response_model=UserResponse)
async def currect_user(uid: CurrentUserId, service: UserServiceDep):
    return await service.get(uid)
