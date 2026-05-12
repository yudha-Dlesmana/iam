from fastapi import Response
from src.core.config import settings

def set_auth_cookie(
    response: Response, 
    access_token: str, 
    refresh_token: str, 
    csrf_token: str
):
    # set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict" if settings.is_production else "lax"
    )
    # set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict" if settings.is_production else "lax"
    )
    # set csrf token cookie
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict" if settings.is_production else "lax"
    )
    pass

def clear_auth_cookie(
    response: Response
):
    # delete 3 cookie
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="csrf_token")
    pass

