from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions.base import AppException


async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppException)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
