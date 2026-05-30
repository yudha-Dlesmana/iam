import json
from fastapi import APIRouter
from jwt.algorithms import RSAAlgorithm

from src.core.config import settings

router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
async def jwks():
    jwk = json.load(RSAAlgorithm.to_jwk(settings.jwt_public_key))
    jwk.update({"use": "sig", "alg": "RS256", "kid": "iam-key-1"})
    return {"keys": [jwk]}
