import re
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from src.schemas.base_schema import BaseResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            success=False,
            message=exc.detail,
            data=None
        ).model_dump()
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [
        f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=BaseResponse(
            success=False,
            message="; ".join(errors),
            data=None
        ).model_dump()
    )

async def integrity_error_handler(_request: Request, exc: IntegrityError):
    if exc.orig:
        code = exc.orig.args[0]
        msg = exc.orig.args[1]

        if code == 1062:
            match = re.search(r"for key '[\w]+\.([\w]+)'", msg)
            column = match.group(1) if match else "field"
            return JSONResponse(
                status_code=409,
                content=BaseResponse(success=False, message=f"{column} already exists", data=None).model_dump()
            )

        if code == 1452:
            match = re.search(r"FOREIGN KEY \(`(\w+)`\)", msg)
            column = match.group(1) if match else "field"
            return JSONResponse(
                status_code=404,
                content=BaseResponse(success=False, message=f"{column} not found", data=None).model_dump()
            )

    return JSONResponse(
        status_code=409,
        content=BaseResponse(success=False, message="Conflict", data=None).model_dump()
    )

async def operational_error_handler(_request: Request, _exc: OperationalError):
    return JSONResponse(
        status_code=503,
        content=BaseResponse(success=False, message="Database unavailable", data=None).model_dump()
    )

# -- Handler Registration --

from fastapi import FastAPI

def register_exception_handlers(app: FastAPI) -> None:
    handlers = [
        (HTTPException, http_exception_handler),
        (RequestValidationError, validation_error_handler),
        (IntegrityError, integrity_error_handler),
        (OperationalError, operational_error_handler),
    ]

    for exc_class, handler in handlers:
        app.add_exception_handler(exc_class, handler)
