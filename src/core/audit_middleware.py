from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.context import ip_var
from src.lib.http import client_ip


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = ip_var.set(client_ip(request))
        try:
            return await call_next(request)
        finally:
            ip_var.reset(token)


def register_audit_middleware(app: FastAPI) -> None:
    app.add_middleware(AuditContextMiddleware)
