from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def status():
    return {
        "status": "running"
    }