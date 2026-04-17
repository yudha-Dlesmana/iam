from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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

async def validation_exception_handler(request: Request, exc: RequestValidationError):
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