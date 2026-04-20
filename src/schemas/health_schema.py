from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    databse: str
    other_service: str