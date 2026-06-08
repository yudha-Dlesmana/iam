from typing import Annotated
from fastapi import APIRouter, Cookie, Request, Response, status

from src.core.config import settings
from src.core.security import REFRESH_TTL
from src.exceptions.base import UnauthorizedError, ForbiddenError
from src.lib.deps import AuthServiceDep, CurrentUserId, UserServiceDep
from src.lib.http import client_ip
from src.schemas.auth import LoginRequest, TokenResponse, SessionResponse
from src.schemas.user import UserResponse


router = APIRouter(prefix="/auth", tags=["authentication"])

REFRESH_COOKIE = "refresh_token"
COOKIE_PATH = "/"
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


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        httponly=True,
        secure=settings.is_production,
        samesite=_SAMESITE,
        path=COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


def _check_origin(request: Request) -> None:
    sec_fetch = request.headers.get("sec-fetch-site")
    if sec_fetch in {"same-origin", "same-site"}:
        return
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins:
        return
    raise ForbiddenError("cross-site request rejected")


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, request: Request, response: Response, service: AuthServiceDep
):
    pair = await service.login(
        data.email,
        data.password,
        ip=client_ip(request),
        ua=request.headers.get("user-agent", ""),
    )
    _set_refresh_cookie(response, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    _check_origin(request=request)
    if not refresh_token:
        raise UnauthorizedError("missing refresh token")
    pair = await service.refresh(refresh_token, ip=client_ip(request))
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
    _clear_refresh_cookie(response)


@router.post("/all-logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    if refresh_token:
        await service.logout_all(refresh_token)
    _clear_refresh_cookie(response)


@router.get("/sessions", response_model=list[SessionResponse])
async def sessions(uid: CurrentUserId, service: AuthServiceDep):
    return await service.sessions(uid)


@router.get("/sessions/current", response_model=SessionResponse)
async def current_session(
    uid: CurrentUserId,
    service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie(include_in_schema=False)] = None,
):
    if not refresh_token:
        raise UnauthorizedError("missing refresh token")
    return await service.current_session(refresh_token, uid)


@router.get("/current-user", response_model=UserResponse)
async def current_user(uid: CurrentUserId, service: UserServiceDep):
    return await service.get(uid)
