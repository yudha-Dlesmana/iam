from pydantic import BaseModel

class GoogleUserInfo(BaseModel):
    sub: str
    email: str
    email_verified: bool
    name: str | None = None
    picture: str | None = None

class OAuhtCreateRequest(BaseModel):
    email: str
    provider:str
    provider_user_id: str
    role_id: int | None = None

