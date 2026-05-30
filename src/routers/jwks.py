import json
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter
from jwt.algorithms import RSAAlgorithm

from src.core.config import settings

router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
async def jwks():
    key = load_pem_public_key(settings.jwt_public_key.encode())
    jwk = json.loads(RSAAlgorithm.to_jwk(key))
    jwk.update({"use": "sig", "alg": "RS256", "kid": "iam-key-1"})
    return {"keys": [jwk]}
