from fastapi import FastAPI
from fastapi.responses import RedirectResponse

import src.models
from src.core.logger import setup_logging
from src.core.cors import setup_cors
from src.core.exception_handler import register_exception_handlers
from src.routers.api_router import api_router


app = FastAPI(
    title="FastAPI Starter",
    description="",
    version="0.0.1",
    swagger_ui_parameters={"withCredentials": True}
)

setup_logging()
setup_cors(app)

register_exception_handlers(app)

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(api_router)