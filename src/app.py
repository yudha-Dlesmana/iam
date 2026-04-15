import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from src.core.database import engine
from src.routers.health_router import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Database connection failed: {e.orig if hasattr(e, 'orig') else e}")
        os._exit(1)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(health_router)