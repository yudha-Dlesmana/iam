from fastapi import FastAPI
from fastapi.responses import RedirectResponse

import src.models
from src.core.exception_handler import register_exception_handlers
from src.routers.api_router import api_router


app = FastAPI()

register_exception_handlers(app)

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(api_router)