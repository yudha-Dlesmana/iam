from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: str | None
    actor_email: str | None = None
    action: str
    target_type: str
    target_id: str
    target_email: str | None = None
    meta: dict | None
    ip: str | None
    created_at: datetime
