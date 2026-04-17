from pydantic import BaseModel, Field


class RoleRequest (BaseModel):
    name: str = Field(..., min_length=1, strip_whitespace=True)

class RoleResponse(BaseModel):
    id: int 
    name: str

    model_config = {"from_attributes": True}