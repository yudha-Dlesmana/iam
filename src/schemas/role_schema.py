from pydantic import BaseModel, StringConstraints
from typing import Annotated


class RoleRequest (BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

class RoleResponse(BaseModel):
    id: int 
    name: str

    model_config = {"from_attributes": True}