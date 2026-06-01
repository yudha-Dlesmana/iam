import json
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter
from jwt.algorithms import RSAAlgorithm

from src.core.keys import all_public_keys


router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
async def jwks():
    out = []
    for kid, pem in all_public_keys().items():
        key = load_pem_public_key(pem.encode())
        jwk = json.loads(RSAAlgorithm.to_jwk(key))
        jwk.update({"use": "sig", "alg": "RS256", "kid": kid})
        out.append(jwk)
    return {"keys": out}
