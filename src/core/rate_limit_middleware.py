from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.redis import redis_client
from src.lib.http import client_ip
from src.lib.rate_limit import hit


_EXEMPT = {"/v1/health", "/.well-known/jwks.json"}


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in _EXEMPT:
            return await call_next(request)

        ip = client_ip(request)
        if ip:
            allowed, retry_after = await hit(
                redis_client,
                f"global:ip:{ip}",
                settings.GLOBAL_RATE_LIMIT,
                settings.GLOBAL_RATE_WINDOW,
            )

            if not allowed:
                return JSONResponse(
                    {"message": "too many requests"},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)


def register_global_rate_limit(app: FastAPI) -> None:
    app.add_middleware(GlobalRateLimitMiddleware)
