from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse
from fastapi import FastAPI

from src.core.database import engine
from src.core.logging import setup_logging
from src.exceptions.handlers import register_exception_handlers
from src.lib.middleware import register_middlewares
from src.routers.api import router as api_router
from src.routers.jwks import router as jwks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


setup_logging()

app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)
register_middlewares(app)


@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")


app.include_router(jwks_router)
app.include_router(api_router)
