from fastapi.responses import RedirectResponse
from fastapi import FastAPI

from src.routers.health_router import router as health_router

app = FastAPI()

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(health_router)