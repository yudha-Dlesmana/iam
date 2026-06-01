from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings


_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

_HSTS = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for k, v in _BASE_HEADERS.items():
            response.headers.setdefault(k, v)
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
        return response


def register_security_headers(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
