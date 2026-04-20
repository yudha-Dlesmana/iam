from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    database: str
    other_service: str