from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse
from fastapi import FastAPI
from src.core.database import engine

from src.routers.api import router as api_router
from src.exceptions.handlers import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI()

register_exception_handlers(app)

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(api_router)