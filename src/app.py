from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, OperationalError

import src.models
from src.core.exception_handler import http_exception_handler, validation_exception_handler, integrity_error_handler, operational_error_handler
from src.routers.api_router import api_router


app = FastAPI()

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(api_router)