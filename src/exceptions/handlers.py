from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.loggin import get_logger
from src.exceptions.base import AppException


log = get_logger(__name__)


async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppException)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = []
    for e in exc.errors():
        field = ".".join(str(x) for x in e["loc"][1:]) or "body"
        msg = e["msg"].removeprefix("Value error, ")
        errors.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=422, content={"message": "validation error", "errors": errors}
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"message": "internal server error"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
