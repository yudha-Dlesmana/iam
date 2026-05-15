from fastapi.responses import RedirectResponse
from fastapi import FastAPI

from src.routers.api_router import router as api_router

app = FastAPI()

@app.get("/", include_in_schema=False)
def default():
    return RedirectResponse("/docs")

app.include_router(api_router)