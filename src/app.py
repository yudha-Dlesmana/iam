import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from src.core.database import engine
from src.routers.health_router import router as health_router


app = FastAPI()

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(health_router)