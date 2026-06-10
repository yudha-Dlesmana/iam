import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.context import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("cf-ray") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = rid
        return response


def register_request_id(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
