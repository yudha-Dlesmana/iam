from fastapi import HTTPException
import httpx
from src.core.config import settings
from src.schemas.oauth_schema import GoogleUserInfo

async def google_oauth(code: str) -> GoogleUserInfo:   
    async with  httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id":settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        token_data = token_resp.json()

        if "error" in token_data:
            raise HTTPException(status_code=400,
            detail=token_data.get("error_description", "Invalid Google code"))

        access_token = token_resp.json().get("access_token")

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return GoogleUserInfo(**user_resp.json())