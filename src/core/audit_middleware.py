from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.audit_context import ip_var


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = ip_var.set(_client_ip(request))
        try:
            return await call_next(request)
        finally:
            ip_var.reset(token)


def register_audit_middleware(app: FastAPI) -> None:
    app.add_middleware(AuditContextMiddleware)
