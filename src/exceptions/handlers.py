from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions.base import AppException


async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppException)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )

async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        f"{'.'.join(str(x) for x in e['loc'][1:]): e['msg']}"
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"message": "validation error", "errors": errors}
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
